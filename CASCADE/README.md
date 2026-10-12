# CASCADE

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23327806.svg)](https://doi.org/10.5281/zenodo.23327806)

**How Agent Failures Propagate in LLM Multi-Agent Systems: Replication Repository**

This repository accompanies the article:

> Ambavaram, R. (2026). *CASCADE: How Agent Failures Propagate in LLM Multi-Agent Systems—A Survey and Taxonomy.* Manuscript submitted to *Artificial Intelligence Review*.

It contains everything needed to inspect, reproduce, and extend the paper's trace study (Section 7):

- the propagation codebook in all three versions;
- 177 non-overlapping condensed execution traces;
- the coder instructions;
- the raw annotations of all three coders;
- the consensus annotations;
- the analysis and figure scripts.

## Repository structure

```
CASCADE/
├── README.md
├── data/
│   ├── condensed_traces/
│   │   ├── main/            136 traces (main sample)
│   │   ├── heldout/         35 traces (held-out test of codebook v1.2)
│   │   └── pilot/           6 traces (pilot)
│   ├── manifest_main.json   per trace: id, system, topology, MAST source file, turns, truncation flag
│   ├── manifest_heldout.json
│   └── manifest_pilot.json
├── annotations/
│   ├── coder1.json          raw codes of coder 1 (keys: pilot, main, heldout)
│   ├── coder2.json          raw codes of coder 2
│   ├── coder3.json          raw codes of coder 3 (main, heldout)
│   └── consensus_annotations.csv   consensus codes for the main and held-out samples
├── codebooks/
│   ├── CASCADE_Codebook_v1.0.pdf   used for the pilot
│   ├── CASCADE_Codebook_v1.1.pdf   frozen before main coding
│   ├── CASCADE_Codebook_v1.2.pdf   frozen before held-out coding
│   └── source/                     Markdown sources whose SHA-256 hashes were recorded at freezing
├── instructions/
│   └── coder_instructions.pdf      procedure and verbatim instruction text given to coders
├── scripts/
│   ├── agreement.py                inter-coder agreement (Fleiss' κ, Cohen's κ, Krippendorff's α, bootstrap CIs)
│   ├── statistics.py               consensus annotations, per-system propagation statistics, Fisher tests
│   ├── figure_generation.py        Figures 1–7 of the paper
│   └── condense_traces.py          regenerates data/condensed_traces/ from the MAST release
├── LICENSE
└── CITATION.cff
```

The scripts write their outputs to `results/`, which is created on first run.

## Quick start

Requirements: Python 3.9 or later. `agreement.py`, `statistics.py`, and `condense_traces.py` use only the standard library. `figure_generation.py` needs `matplotlib` and `numpy`.

```bash
python3 scripts/statistics.py        # consensus codes, Table 5, Fisher tests -> results/statistics.json
python3 scripts/agreement.py         # Table 4 and Fig. 5 statistics          -> results/agreement.json
python3 scripts/figure_generation.py # Figures 1-7                            -> results/figures/
```

Running the scripts reproduces every number reported in Section 7 of the paper. We verified this from a clean copy of the repository.

### Optional: external check and trace regeneration

These steps need the MAST repository:

```bash
git clone https://github.com/multi-agent-systems-failure-taxonomy/mast
git -C mast checkout a70542e541b2104ef8fcd785778179e173fb8d70

# AG2 MathChat check against the release's correctness flags and MAST labels
python3 scripts/statistics.py mast/traces

# Regenerate the condensed traces (byte-identical to data/condensed_traces/)
python3 -I scripts/condense_traces.py mast/traces /tmp/regen/main
python3 -I scripts/condense_traces.py mast/traces /tmp/regen/sets --sets   # pilot and held-out sets
```

## The study in brief

**Sample.** We drew 136 traces from seven open-source multi-agent systems in the MAST release:

- AG2 MathChat;
- AG2 group chat with a verifier;
- MetaGPT;
- ChatDev;
- a multi-agent AppWorld configuration;
- Magentic-One;
- HyperAgent.

We sampled 20 traces per system at random with seed 20261011. AppWorld contributed all 16 of its traces.

**Condensation.** Each trace was condensed into numbered agent turns. Turns longer than 1,450 characters keep their first 1,100 and last 350 characters. Seven long traces also had middle turns omitted, which is marked in each trace and flagged in the manifest.

**Coding.** For each trace, coders recorded:

- the task outcome, and whether a consequential error occurred;
- for the root error: its turn, agent, origin layer, and conflict target;
- the turns and agents that consumed it, giving blast radius and hop depth;
- whether it was detected (with latency), corrected, and whether it reached the output;
- the propagation mechanisms;
- the propagation regime.

See the codebook.

**Coders.** Three independent language-model coders were used: coder 1 Claude Opus, coder 2 Claude Sonnet, and coder 3 Claude Haiku (Anthropic). Their agreement shows that the codebook can be applied consistently. It does not show that the codes match expert human judgment. A replication with human annotators is described in `instructions/coder_instructions.pdf`, Section 8.

**Codebook versions.**

| Version | Used for | SHA-256 of Markdown source | Frozen (UTC) |
|---|---|---|---|
| v1.0 | Pilot (6 traces, 2 coders) | `11c98939…6dec007` | — |
| v1.1 | Main sample (136 traces) | `3ecb1a1f…ff337b4c` | 2026-10-11 23:50 |
| v1.2 | Held-out sample (35 traces) | `a25caa89…3bc6c` | 2026-10-12 00:14 |

The full hashes and freeze times are in `codebooks/source/PREREGISTERED_AT.txt`. To verify a hash, run `sha256sum codebooks/source/*.md`. The PDFs are typeset from these sources.

**Consensus rules.**

- Categorical fields take the majority of the three coders. Fields that depend on an error are aggregated over the coders who coded one.
- Blast radius and hop depth take the median.
- Detection latency is the median over coders who coded a dated detection, reported when at least two did.
- An empty cell in `consensus_annotations.csv` means that no majority was reached.

## Annotation format

Each record in `annotations/coderN.json` has these keys:

- `id`;
- `outcome`, `error_present`;
- `origin_turn`, `origin_agent`, `origin_layer`, `target`;
- `consuming_turns`, `consumer_agents`, `blast_radius`, `hop_depth`, `propagated`;
- `detected`, `detection_turn`, `detector_agent`, `corrected`, `reached_output`;
- `mechanisms`, `regime`;
- `evidence`: a short justification that cites turn numbers.

Value sets are defined in the codebook.

## Data provenance

The condensed traces are derived from the trace data of the MAST project: Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", NeurIPS 2025 Datasets and Benchmarks Track. We condensed the traces from the project's GitHub repository (https://github.com/multi-agent-systems-failure-taxonomy/mast, commit `a70542e`). The same project publishes its trace dataset, covering the same seven systems with the raw trace text, on Hugging Face as MAST-Data (https://huggingface.co/datasets/mcemri/MAST-Data) under the **Creative Commons Attribution 4.0 (CC BY 4.0)** license.

CC BY 4.0 permits redistribution and adaptation, provided that credit is given and changes are indicated. Accordingly:

- this repository credits the MAST authors here, in `LICENSE`, and in `CITATION.cff`;
- the changes we made, namely condensation into numbered turns, clipping of long turns, omission of middle turns in seven traces, and removal of framework boilerplate, are described above and marked in every trace header.

The GitHub repository itself carries no license file. We rely on the CC BY 4.0 release of the same data; if in doubt, confirm with the MAST authors.

**AppWorld personal data.** The AppWorld traces contain names, e-mail addresses, and passwords. AppWorld's authors describe its data as "realistic but simulated data from digital lives and activities of ~100 fictitious users", created as 106 fictitious people with generated app activity (Trivedi et al., ACL 2024, Sections 1 and 2.3). Their ethics statement notes that it is "still possible, though unlikely" that the data contains uniquely identifiable personal information they missed. We have left the traces unchanged.

## Notes

- `codebooks/source/PREREGISTERED_AT.txt` records a planned held-out sample of 36 traces. Only 5 unused ChatDev traces remained, so the held-out sample has 35 traces. The record is kept as written at the time.
- The held-out set contains no AppWorld traces, because all 16 were used in the main sample.
- coder3 did not take part in the pilot, which used two coders.

## Citation

If you use this repository, please cite it and the MAST release:

> Ambavaram, R. (2026). *CASCADE Replication Package* (Version 1.0). Zenodo. https://doi.org/10.5281/zenodo.23327807

Once the article is published, please cite the article as well (see `CITATION.cff`).

## License

See `LICENSE`.
