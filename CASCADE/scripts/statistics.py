"""Consensus annotations and propagation statistics for the CASCADE trace study.

1. Builds consensus codes from the three coders: majority vote for categorical fields
   (fields that depend on an error are aggregated over the coders who coded one), the median
   for blast radius and hop depth, and the median detection latency over coders who coded a
   dated detection (reported only when at least two did).
2. Writes annotations/consensus_annotations.csv (main and held-out samples).
3. Computes per-system and overall propagation statistics (Table 5 of the paper) and the two
   Fisher exact tests reported in Section 7.4.
4. Optionally checks the AG2 MathChat traces against the MAST release's correctness flags and
   failure-mode labels (pass the path to the MAST repository's traces/ folder).

Usage:  python3 scripts/statistics.py [path/to/mast/traces]
Outputs: results/consensus_main.json, results/consensus_heldout.json, results/statistics.json,
         annotations/consensus_annotations.csv
"""
import collections
import csv
import json
import os
import sys
from math import comb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODERS = ["coder1", "coder2", "coder3"]
MECHANISMS = ["RELAY", "SNOWBALL", "ENDORSEMENT", "ARTIFACT", "LOOP", "DELEGATION"]
ERROR_FIELDS = ["origin_layer", "target", "propagated", "detected", "corrected", "reached_output", "regime"]
SYSTEMS = ["AG2 MathChat", "AG2 GroupChat + verifier", "MetaGPT", "ChatDev", "HyperAgent", "AppWorld multi-agent", "Magentic-One"]


def load_codes(sample):
    out = {}
    for c in CODERS:
        d = json.load(open(os.path.join(ROOT, "annotations", f"{c}.json")))
        out[c] = {r["id"]: r for r in d[sample]}
    return out


def load_manifest(sample):
    return {o["id"]: o for o in json.load(open(os.path.join(ROOT, "data", f"manifest_{sample}.json")))}


def cat(codes, c, i, f):
    v = codes[c][i].get(f)
    return v.strip().upper() if isinstance(v, str) else v


def num(codes, c, i, f):
    try:
        return float(codes[c][i].get(f))
    except (TypeError, ValueError):
        return 0.0


def median(xs):
    """Median (the standard-library statistics module is not imported because this file shares its name)."""
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def majority(vals):
    top = collections.Counter(vals).most_common()
    return top[0][0] if top[0][1] >= 2 else None


def consensus(sample):
    codes = load_codes(sample)
    cons = {}
    for i in sorted(codes["coder1"]):
        r = {f: majority([cat(codes, c, i, f) for c in CODERS]) for f in ["outcome", "error_present"]}
        if r["error_present"] == "YES":
            yes = [c for c in CODERS if cat(codes, c, i, "error_present") == "YES"]
            for f in ERROR_FIELDS:
                r[f] = majority([cat(codes, c, i, f) for c in yes]) if len(yes) >= 2 else None
            for f in ["blast_radius", "hop_depth"]:
                r[f] = median([num(codes, c, i, f) for c in yes])
            r["mech"] = {m: sum(m in [str(x).upper() for x in (codes[c][i].get("mechanisms") or [])] for c in yes) >= 2 for m in MECHANISMS}
            lat = []
            for c in yes:
                d, o = codes[c][i].get("detection_turn"), codes[c][i].get("origin_turn")
                if cat(codes, c, i, "detected") == "YES" and isinstance(d, (int, float)) and isinstance(o, (int, float)) and d >= o:
                    lat.append(d - o)
            r["latency"] = median(lat) if len(lat) >= 2 else None
        cons[i] = r
    return cons


def summarize(cons, ids):
    E = [i for i in ids if cons[i]["error_present"] == "YES"]

    def frac(xs, f, v):
        xs = [x for x in xs if cons[x].get(f) is not None]
        return [sum(cons[x][f] == v for x in xs), len(xs)]

    br = [cons[x]["blast_radius"] for x in E]
    hd = [cons[x]["hop_depth"] for x in E]
    lat = [cons[x]["latency"] for x in E if cons[x].get("latency") is not None]
    return dict(
        n=len(ids), failed=frac(ids, "outcome", "FAILURE"), succeeded=frac(ids, "outcome", "SUCCESS"), errors=len(E),
        spread=[sum(cons[x].get("regime") in ("P1_PROPAGATED", "P2_AMPLIFIED", "P3_EMERGENT") for x in E),
                sum(cons[x].get("regime") is not None for x in E)],
        amplified=frac(E, "regime", "P2_AMPLIFIED"), contained=frac(E, "regime", "P0_CONTAINED"),
        detected=frac(E, "detected", "YES"), corrected=frac(E, "corrected", "YES"), reached_output=frac(E, "reached_output", "YES"),
        blast_radius_mean=round(sum(br) / len(br), 2) if br else None, hop_depth_mean=round(sum(hd) / len(hd), 2) if hd else None,
        detection_latency_median=median(lat) if lat else None, detection_latency_n=len(lat),
        origin_layers=dict(collections.Counter(str(cons[x].get("origin_layer")) for x in E)),
        mechanisms={m: sum(cons[x]["mech"][m] for x in E) for m in MECHANISMS},
        regimes=dict(collections.Counter(str(cons[x].get("regime")) for x in E)))


def fisher(a, b, c, d):
    """Two-sided Fisher exact test for the 2x2 table [[a, b], [c, d]]."""
    n, r1, c1 = a + b + c + d, a + b, a + c
    p0 = comb(r1, a) * comb(n - r1, c1 - a) / comb(n, c1)
    return sum(comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
               for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1)
               if comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1) <= p0 + 1e-12)


def tests(cons):
    E = [i for i in cons if cons[i]["error_present"] == "YES"]
    spread = lambda i: cons[i].get("regime") in ("P1_PROPAGATED", "P2_AMPLIFIED")
    contained = lambda i: cons[i].get("regime") == "P0_CONTAINED"
    t1 = [sum(spread(i) and cons[i]["outcome"] == "FAILURE" for i in E), sum(spread(i) and cons[i]["outcome"] == "SUCCESS" for i in E),
          sum(contained(i) and cons[i]["outcome"] == "FAILURE" for i in E), sum(contained(i) and cons[i]["outcome"] == "SUCCESS" for i in E)]
    known = lambda i, f: cons[i].get(f) is not None
    det = lambda i: cons[i].get("detected") == "YES"
    rea = lambda i: cons[i].get("reached_output") == "YES"
    t2 = [sum(det(i) and rea(i) for i in E), sum(det(i) and known(i, "reached_output") and not rea(i) for i in E),
          sum(known(i, "detected") and not det(i) and rea(i) for i in E),
          sum(known(i, "detected") and not det(i) and known(i, "reached_output") and not rea(i) for i in E)]
    return {"spread_vs_failure": dict(table=t1, rows="spread (P1-P2) / contained (P0)", cols="failure / success", p=fisher(*t1)),
            "detected_vs_reached_output": dict(table=t2, rows="detected / not detected", cols="reached output / did not", p=fisher(*t2))}


def external_check(cons, man, mast_traces):
    rows = []
    for i, o in man.items():
        if o["system"] != "AG2 MathChat":
            continue
        d = json.load(open(os.path.join(mast_traces, o["src"])))
        rows.append(dict(id=i, release_correct=bool(d["other_data"].get("correct")), consensus_outcome=cons[i]["outcome"],
                         mast_any_failure_mode=any(str(v).lower() == "yes" for v in (o.get("mast_human") or {}).values()),
                         consensus_error=cons[i]["error_present"]))
    return dict(n=len(rows), outcome_matches_release=sum((r["consensus_outcome"] == "SUCCESS") == r["release_correct"] for r in rows),
                error_matches_mast_labels=sum((r["consensus_error"] == "YES") == r["mast_any_failure_mode"] for r in rows), rows=rows)


def write_csv(all_cons):
    cols = ["sample", "id", "system", "topology", "turns", "truncated", "outcome", "error_present", "origin_layer", "target", "propagated",
            "regime", "blast_radius", "hop_depth", "detected", "corrected", "reached_output", "detection_latency_turns"] + \
           ["mech_" + m.lower() for m in MECHANISMS]
    with open(os.path.join(ROOT, "annotations", "consensus_annotations.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for sample, (cons, man) in all_cons.items():
            for i in sorted(cons):
                c, o = cons[i], man[i]
                w.writerow([sample, i, o["system"], o["topology"], o["turns"], o["truncated"], c.get("outcome"), c.get("error_present"),
                            c.get("origin_layer"), c.get("target"), c.get("propagated"), c.get("regime"), c.get("blast_radius"),
                            c.get("hop_depth"), c.get("detected"), c.get("corrected"), c.get("reached_output"), c.get("latency")]
                           + [int(c["mech"][m]) if "mech" in c else "" for m in MECHANISMS])


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    all_cons = {}
    for sample in ["main", "heldout"]:
        cons, man = consensus(sample), load_manifest(sample)
        all_cons[sample] = (cons, man)
        json.dump(cons, open(os.path.join(ROOT, "results", f"consensus_{sample}.json"), "w"), indent=1)
    write_csv(all_cons)
    cons, man = all_cons["main"]
    out = {"systems": {s: summarize(cons, [i for i in sorted(cons) if man[i]["system"] == s]) for s in SYSTEMS},
           "overall": summarize(cons, sorted(cons)), "fisher_tests": tests(cons)}
    if len(sys.argv) > 1:
        out["external_check_mathchat"] = external_check(cons, man, sys.argv[1])
    json.dump(out, open(os.path.join(ROOT, "results", "statistics.json"), "w"), indent=1)
    for s, d in list(out["systems"].items()) + [("All systems", out["overall"])]:
        print(f"{s:26s} n={d['n']:3d} failed={d['failed']} errors={d['errors']} spread={d['spread']} amplified={d['amplified']} "
              f"detected={d['detected']} corrected={d['corrected']} reached={d['reached_output']} "
              f"blast={d['blast_radius_mean']} hops={d['hop_depth_mean']} latency={d['detection_latency_median']} ({d['detection_latency_n']})")
    for k, v in out["fisher_tests"].items():
        print(f"{k}: table {v['table']}, p = {v['p']:.2g}")
    if "external_check_mathchat" in out:
        e = out["external_check_mathchat"]
        print(f"MathChat external check: outcome matches release {e['outcome_matches_release']}/{e['n']}, "
              f"error presence matches MAST labels {e['error_matches_mast_labels']}/{e['n']}")
