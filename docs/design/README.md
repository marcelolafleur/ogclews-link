# Design record

The thinking behind `ogclews-link`: why the OG-Core ⇄ CLEWS coupling is built the way it is.
The code is the *what*; these docs are the *why*. They are reference, not runtime — nothing
imports them.

| file | what it is |
|---|---|
| [og-clews-denovo-analysis.md](og-clews-denovo-analysis.md) | **The charter.** A fresh read of both models' theory: the structural seam, the ranked interaction surface (the 6 channels), the two-thread architecture (theoretical-best dual loop vs. practical staged soft-link), and the MUIOGO / multi-country plan. `contract.py` and `iterate.py` cite this. |
| [ogcore-clews-integration-worklog.md](ogcore-clews-integration-worklog.md) | The running log of the integration effort — decisions, dead ends, findings. |
| [ogcore-clews-integration-synthesis-report.md](ogcore-clews-integration-synthesis-report.md) | A synthesis of the integration findings. |
| [energy-price-transmission.md](energy-price-transmission.md) | How a CLEWS electricity-price change reaches OG-Core: the four transmissions (`tau_c` / own-`Z` / cost-push / the `energy_full` composite), why their GDP signs disagree, the 4-way PHL result, country-generality, and the link-side ceiling vs. the [energy-as-production-input-spec.md](energy-as-production-input-spec.md) endpoint. |

## Provenance

These were authored in `~/Projects/ogclews-schema/correspondence/` — an **unversioned**
scratch directory — and copied here so they live under version control alongside the code
they explain. The originals there also include a third-party OG-Core checkout, the superseded
prior channel registry (`integration_channel_registry.json`), and supporting notes
(course assessment, fiscal findings, diagram templates) not copied here.
