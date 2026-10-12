# CASCADE

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.xxxxxxx.svg)](https://doi.org/10.5281/zenodo.xxxxxxx)

**How Agent Failures Propagate in LLM Multi-Agent Systems: Replication Package**

This repository accompanies the article *CASCADE: How Agent Failures Propagate in LLM Multi-Agent Systems—A Survey and Taxonomy* (Ambavaram, 2026; submitted to *Artificial Intelligence Review*).

**All files are in the [`CASCADE/`](CASCADE/) folder.** Its [README](CASCADE/README.md) describes the contents, the study and how to reproduce every number. Run the scripts from inside that folder:

```bash
cd CASCADE
python3 scripts/statistics.py
python3 scripts/agreement.py
python3 scripts/figure_generation.py
```

## Citation

> Ambavaram, R. (2026). *CASCADE Replication Package* (Version 1.0). Zenodo. https://doi.org/10.5281/zenodo.xxxxxxx

Please also cite the MAST release, from which the condensed traces are adapted (see `CASCADE/README.md`).

## License

Scripts: MIT. Codebooks, annotations and documentation: CC BY 4.0. Condensed traces: adapted from MAST-Data under CC BY 4.0. See [LICENSE](LICENSE).
