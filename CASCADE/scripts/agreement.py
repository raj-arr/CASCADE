"""Inter-coder agreement for the CASCADE trace study.

Computes, for the main and held-out samples:
  * Fleiss' kappa and pairwise Cohen's kappa for categorical fields,
  * Krippendorff's alpha (interval metric) for blast radius and hop depth,
  * pairwise exact and within-two-turn agreement on the root-error turn,
  * 95% bootstrap intervals (2,000 resamples of traces, seed 1).

Fields that depend on an error being present are evaluated on traces in which all three
coders coded an error. Standard library only.

Usage:  python3 scripts/agreement.py            (writes results/agreement.json)
"""
import collections
import itertools
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODERS = ["coder1", "coder2", "coder3"]
MECHANISMS = ["RELAY", "SNOWBALL", "ENDORSEMENT", "ARTIFACT", "LOOP", "DELEGATION"]
ALL_TRACE_FIELDS = ["outcome", "error_present"]
ERROR_FIELDS = ["origin_layer", "target", "propagated", "detected", "corrected", "reached_output", "regime"]
COUNT_FIELDS = ["blast_radius", "hop_depth"]


def load_codes(sample):
    out = {}
    for c in CODERS:
        d = json.load(open(os.path.join(ROOT, "annotations", f"{c}.json")))
        out[c] = {r["id"]: r for r in d[sample]}
    return out


def cat(codes, c, i, f):
    v = codes[c][i].get(f)
    return str(v.strip().upper() if isinstance(v, str) else v)


def num(codes, c, i, f):
    try:
        return float(codes[c][i].get(f))
    except (TypeError, ValueError):
        return 0.0


def cohen(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = collections.Counter(a), collections.Counter(b)
    pe = sum(pa[k] * pb[k] for k in set(a) | set(b)) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def fleiss(rows):
    n, k = len(rows), len(rows[0])
    p = [(sum(v * v for v in collections.Counter(r).values()) - k) / (k * (k - 1)) for r in rows]
    pbar = sum(p) / n
    pj = collections.Counter(x for r in rows for x in r)
    pe = sum((v / (n * k)) ** 2 for v in pj.values())
    return (pbar - pe) / (1 - pe) if pe < 1 else 1.0


def kripp_interval(rows):
    vals = [v for r in rows for v in r]
    n = len(vals)
    do = sum(sum((a - b) ** 2 for a, b in itertools.permutations(r, 2)) / (len(r) - 1) for r in rows) / n
    de = sum((a - b) ** 2 for a, b in itertools.permutations(vals, 2)) / (n * (n - 1))
    return 1 - do / de if de > 0 else 1.0


def bootstrap(stat, ids, reps=2000, seed=1):
    random.seed(seed)
    draws = sorted(stat([random.choice(ids) for _ in ids]) for _ in range(reps))
    return round(draws[int(0.025 * reps)], 2), round(draws[int(0.975 * reps)], 2)


def analyze(sample):
    codes = load_codes(sample)
    ids = sorted(codes["coder1"])
    yes = [i for i in ids if all(cat(codes, c, i, "error_present") == "YES" for c in CODERS)]
    res = {"n_traces": len(ids), "n_all_coders_error": len(yes), "fields": {}}

    def categorical(f, sub):
        rows = lambda s: [[cat(codes, c, i, f) for c in CODERS] for i in s]
        r = rows(sub)
        pairs = [cohen([x[a] for x in r], [x[b] for x in r]) for a, b in [(0, 1), (0, 2), (1, 2)]]
        return dict(n=len(sub), fleiss_kappa=round(fleiss(r), 3), ci95=bootstrap(lambda s: fleiss(rows(s)), sub),
                    cohen_c1c2=round(pairs[0], 3), cohen_c1c3=round(pairs[1], 3), cohen_c2c3=round(pairs[2], 3),
                    all_three_agree=round(sum(len(set(x)) == 1 for x in r) / len(r), 3))

    for f in ALL_TRACE_FIELDS:
        res["fields"][f] = categorical(f, ids)
    for f in ERROR_FIELDS:
        res["fields"][f] = categorical(f, yes)
    for m in MECHANISMS:
        for c in CODERS:
            for i in yes:
                codes[c][i]["_mech"] = "YES" if m in [str(x).upper() for x in (codes[c][i].get("mechanisms") or [])] else "NO"
        res["fields"]["mechanism_" + m.lower()] = categorical("_mech", yes)
    for f in COUNT_FIELDS:
        rows = lambda s: [[num(codes, c, i, f) for c in CODERS] for i in s]
        res["fields"][f] = dict(n=len(yes), kripp_alpha_interval=round(kripp_interval(rows(yes)), 3),
                                ci95=bootstrap(lambda s: kripp_interval(rows(s)), yes),
                                all_three_equal=round(sum(len(set(r)) == 1 for r in rows(yes)) / len(yes), 3))
    exact, near = [], []
    for i in yes:
        t = [num(codes, c, i, "origin_turn") for c in CODERS]
        for a, b in [(0, 1), (0, 2), (1, 2)]:
            exact.append(t[a] == t[b])
            near.append(abs(t[a] - t[b]) <= 2)
    res["fields"]["origin_turn"] = dict(n=len(yes), pairwise_exact=round(sum(exact) / len(exact), 3),
                                        pairwise_within_2=round(sum(near) / len(near), 3))
    return res


if __name__ == "__main__":
    out = {s: analyze(s) for s in ["main", "heldout"]}
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "results", "agreement.json"), "w"), indent=1)
    for s, r in out.items():
        print(f"\n{s}: {r['n_traces']} traces, {r['n_all_coders_error']} with an error coded by all three coders")
        for f, v in r["fields"].items():
            k = v.get("fleiss_kappa", v.get("kripp_alpha_interval"))
            print(f"  {f:28s} {k if k is not None else '':>7} {v.get('ci95', '')}"
                  + (f"  exact {v['pairwise_exact']}, within 2 {v['pairwise_within_2']}" if f == "origin_turn" else ""))
