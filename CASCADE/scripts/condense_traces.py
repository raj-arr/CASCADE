"""Condense heterogeneous MAST traces into numbered agent turns for propagation coding.

Regenerates data/condensed_traces/ deterministically from the MAST release (commit a70542e).
  Main sample (136 traces):    python3 -I scripts/condense_traces.py <mast/traces> <out_dir>
  Pilot and held-out sets:     python3 -I scripts/condense_traces.py <mast/traces> <out_dir> --sets
With --sets, the script condenses the pools drawn with seeds 777 (pilot) and 4242 (held-out) and keeps
traces outside the main sample: the first per system (pilot) and the first six per system not in the
main or pilot sets (held-out).
Trace files are treated as untrusted data: they are only parsed as text/JSON."""
import json, re, os, sys, glob, random
ROOT, OUT = sys.argv[1], sys.argv[2]
if len(sys.argv) > 3 and sys.argv[3] == "--sets":
    import subprocess, shutil, collections as _c
    here = os.path.abspath(__file__)
    repo = os.path.dirname(os.path.dirname(here))
    def _condense(seed, out):
        subprocess.run([sys.executable, "-I", here, ROOT, out, str(seed)], check=True, stdout=subprocess.DEVNULL)
        return json.load(open(os.path.join(out, "_manifest.json")))
    main = {o["id"] for o in json.load(open(os.path.join(repo, "data", "manifest_main.json")))}
    sets = {}
    for name, seed, k in [("pilot", 777, 1), ("heldout", 4242, 6)]:
        pool = _condense(seed, os.path.join(OUT, "pool_" + name)); os.makedirs(os.path.join(OUT, name), exist_ok=True)
        cnt = _c.Counter(); keep = []
        exclude = main | set(o["id"] for o in sets.get("pilot", []))
        for o in pool:
            if o["id"] in exclude or cnt[o["system"]] >= k: continue
            cnt[o["system"]] += 1; keep.append(o)
            shutil.copy(os.path.join(OUT, "pool_" + name, o["id"] + ".txt"), os.path.join(OUT, name))
        sets[name] = keep
        json.dump(keep, open(os.path.join(OUT, name, "_manifest.json"), "w"), indent=1)
        print(name, len(keep), dict(cnt))
    sys.exit(0)
SEED = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != '--sets' else 20261011  # 20261011 = main sample; 777 = pilot pool; 4242 = held-out pool
os.makedirs(OUT, exist_ok=True)
random.seed(SEED)
HEAD, TAIL, TOTAL = 1100, 350, 48000

def clip(t, h, tl):
    t = re.sub(r'\n{3,}', '\n\n', t.strip())
    if len(t) <= h + tl + 40: return t
    return t[:h] + f"\n[... {len(t)-h-tl} characters omitted ...]\n" + t[-tl:]

def render(turns):
    for h, tl in [(HEAD, TAIL), (700, 250), (450, 150), (300, 100)]:
        body = "\n\n".join(f"[T{i}] {s}:\n{clip(x, h, tl)}" for i, (s, x) in enumerate(turns, 1))
        if len(body) <= TOTAL: return body, False
    # still too long: keep the first 45% and the last 35% of turns; mark the gap
    n = len(turns); a = int(n * .45); b = n - int(n * .35)
    parts = [f"[T{i}] {s}:\n{clip(x, 300, 100)}" for i, (s, x) in enumerate(turns, 1) if i <= a or i > b]
    parts.insert(a, f"[... turns T{a+1}–T{b} omitted for length ({b-a} turns) ...]")
    return "\n\n".join(parts), True

def blocks_by_marker(lines, pat, speaker_fn, start_pat=None):
    turns, cur, spk = [], [], None
    started = start_pat is None
    for l in lines:
        if not started:
            if re.search(start_pat, l): started = True
            else: continue
        m = re.search(pat, l)
        if m:
            if spk is not None and ''.join(cur).strip(): turns.append((spk, '\n'.join(cur)))
            spk, cur = speaker_fn(m), [l[m.end():]]
        elif spk is not None:
            cur.append(l)
    if spk is not None and ''.join(cur).strip(): turns.append((spk, '\n'.join(cur)))
    return turns

out = []
def emit(system, topology, tid, task, truth, turns, meta=None):
    body, trunc = render(turns)
    hdr = (f"TRACE {tid}\nSYSTEM: {system}\nTOPOLOGY: {topology}\nTASK: {clip(task, 1500, 300)}\n"
           f"REFERENCE OUTCOME (if known): {truth or 'not provided; judge from the trace'}\n"
           f"TURNS: {len(turns)}{' (middle turns omitted for length)' if trunc else ''}\n\n")
    open(os.path.join(OUT, tid + ".txt"), "w").write(hdr + body)
    out.append(dict(id=tid, system=system, topology=topology, turns=len(turns), chars=len(hdr+body), truncated=trunc, **(meta or {})))

def pick(files, k): files = sorted(files); random.shuffle(files); return files[:k]

# 1. AG2 MathChat (two agents: LLM assistant + code-executing proxy)
for f in pick(glob.glob(f"{ROOT}/AG2/*.json"), 20):
    d = json.load(open(f)); od = d.get("other_data", {})
    turns = [(t.get("name") or t.get("role"), "\n".join(t["content"]) if isinstance(t["content"], list) else str(t["content"])) for t in d["trajectory"]]
    truth = f"seed answer {od.get('seed_answer')}; perturbation: {od.get('perturbation_type')}; original question: {od.get('seed_question')}"
    emit("AG2 MathChat", "two-agent loop (assistant + executor)", "ag2_" + d["instance_id"][:8], " ".join(d["problem_statement"]), truth, turns,
         dict(mast_human=d.get("note", {}).get("options"), src=os.path.relpath(f, ROOT)))

# 2. AG2 group chat with verifier (MAST topology intervention traces)
for f in pick(glob.glob(f"{ROOT}/math_interventions/topology_traces/*.txt"), 20):
    lines = open(f, errors="replace").read().split("\n")
    turns = blocks_by_marker(lines, r"^(assistant|user|Agent_[A-Za-z_]+):", lambda m: m.group(1))
    task = turns[0][1] if turns else ""
    emit("AG2 GroupChat + verifier", "group chat: problem solver, code executor, verifier", "grp_" + os.path.basename(f)[:-4], task, None, turns[1:], dict(src=os.path.relpath(f, ROOT)))

# 3. MetaGPT (SOP pipeline: coder -> tester -> reviewer)
for f in pick(glob.glob(f"{ROOT}/programdev/metagpt/*.txt"), 20):
    txt = open(f, errors="replace").read()
    turns = []
    for blk in re.split(r"\n-{40,}\n", txt):
        m = re.search(r"FROM: (\S+) TO:.*?CONTENT:\n(.*)", blk, re.S)
        if m: turns.append((m.group(1), m.group(2))); continue
        m = re.search(r"NEW MESSAGES:\s*\n\s*\n?([A-Za-z]+):\s*\n(.*)", blk, re.S)
        if m: turns.append((m.group(1), m.group(2)))
    task = turns[0][1] if turns else ""
    emit("MetaGPT", "sequential SOP pipeline (coder, tester, reviewer)", "mgpt_" + os.path.basename(f)[:-4], task, None, turns, dict(src=os.path.relpath(f, ROOT)))

# 4. ChatDev (waterfall of role-pair dialogues)
def chatdev_strip(x):
    x = x.strip()
    if x.startswith("[ChatDev is a software company"):
        k = x.find("]\n")
        if k > 0: x = x[k+2:]
    return x
for d in pick([p for p in glob.glob(f"{ROOT}/programdev/chatdev/*") if os.path.isdir(p)], 20):
    logs = glob.glob(d + "/*.log")
    if not logs: continue
    lines = []
    skip = False
    for l in open(logs[0], errors="replace").read().split("\n"):
        if "flask app.py did not start" in l or "HTTP Request:" in l: continue
        lines.append(l)
    raw = blocks_by_marker(lines, r"INFO\] ([A-Za-z ]+): \*\*(\[[A-Za-z ]+\]|[A-Za-z ]+<->[A-Za-z ]+ on : ([A-Za-z]+), turn \d+)\*\*",
                           lambda m: (m.group(1), m.group(2), m.group(3)))
    turns = []
    phase = ""
    for (spk, tag, ph), x in raw:
        if spk == "System" or "OpenAI_Usage" in x[:200]: continue
        x = re.sub(r"\[\d{4}-[^\]]*INFO\] \*\*\[OpenAI_Usage_Info Receive\]\*\*.*?cost: \$[0-9.]+", "", x, flags=re.S)
        if tag == "[Start Chat]":
            turns.append((f"{spk} (phase instruction)", chatdev_strip(x)))
        elif ph:
            turns.append((f"{spk} [{ph}]", chatdev_strip(x)))
    task = open(glob.glob(d + "/*.prompt")[0]).read() if glob.glob(d + "/*.prompt") else os.path.basename(d)
    emit("ChatDev", "waterfall chain of role-pair dialogues (CEO, CPO, CTO, programmer, reviewer, tester)", "cdev_" + os.path.basename(d), task, None, turns, dict(src=os.path.relpath(d, ROOT)))

# 5. HyperAgent (hierarchical: planner + navigator/editor/executor)
hfiles = [f for f in glob.glob(f"{ROOT}/HyperAgent/*.json")]
nh = 0
for f in pick(hfiles, len(hfiles)):
    if nh >= 20: break
    d = json.load(open(f))
    lines = [l for l in d["trajectory"] if isinstance(l, str)]
    turns = blocks_by_marker(lines, r" - INFO - ((?:Planner|Inner-[A-Za-z]+-Assistant)'s Response|[A-Za-z]+->Planner):",
                             lambda m: m.group(1).replace("'s Response", ""))
    if len(turns) < 3: continue
    nh += 1
    emit("HyperAgent", "hierarchical: planner delegating to navigator, editor, executor", "hyp_" + d["instance_id"][:40], " ".join(d["problem_statement"]) if isinstance(d["problem_statement"], list) else str(d["problem_statement"]), None, turns,
         dict(mast_human=d.get("note", {}).get("options"), src=os.path.relpath(f, ROOT)))

# 6. AppWorld (supervisor star over app agents)
for f in sorted(glob.glob(f"{ROOT}/AppWorld/*.txt")):
    txt = open(f, errors="replace").read()
    m = re.search(r"\*{5,} Task .*?\*{5,}\n(.*?)\n", txt)
    task = m.group(1) if m else ""
    lines = txt.split("\n")
    turns = blocks_by_marker(lines, r"^\s*(Response from [A-Za-z]+ Agent|Message to [A-Za-z]+ Agent|Code Execution Output|Reply from [A-Za-z]+ Agent)\s*$", lambda m: m.group(1))
    ev = re.findall(r'"label": "([^"]+)"', txt)
    emit("AppWorld multi-agent", "star: supervisor agent messaging app-specific agents", "appw_" + os.path.basename(f)[:-4], task,
         ("evaluation labels in log: " + ", ".join(sorted(set(ev)))) if ev else None, turns, dict(src=os.path.relpath(f, ROOT)))

# 7. Magentic-One (orchestrator with web, file, code agents)
mlogs = glob.glob(f"{ROOT}/MagenticOne_GAIA/*/*/0/console_log.txt")
for f in pick(mlogs, 20):
    lines = open(f, errors="replace").read().split("\n")
    turns = blocks_by_marker(lines, r"^---------- ([A-Za-z_]+) ----------", lambda m: m.group(1), start_pat=r"^---------- user ----------")
    exp = os.path.join(os.path.dirname(f), "expected_answer.txt")
    truth = "expected answer: " + open(exp).read().strip() if os.path.exists(exp) else None
    task = turns[0][1] if turns else ""
    tid = "mag_" + f.split("/")[-3][:8]
    emit("Magentic-One", "star: orchestrator with ledger delegating to WebSurfer, FileSurfer, Coder, ComputerTerminal", tid, task, truth, turns[1:], dict(src=os.path.relpath(f, ROOT)))

json.dump(out, open(os.path.join(OUT, "_manifest.json"), "w"), indent=1)
import collections
c = collections.defaultdict(list)
for o in out: c[o["system"]].append(o)
for s, v in c.items():
    print(f"{s:28s} n={len(v):3d} turns med={sorted(x['turns'] for x in v)[len(v)//2]:4d} min={min(x['turns'] for x in v)} chars med={sorted(x['chars'] for x in v)[len(v)//2]} trunc={sum(x['truncated'] for x in v)}")
