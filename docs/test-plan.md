# OG ⇄ CLEWS coupling — test plan

Validate each coupling **part in isolation**, then **combined**, before relying on results.
Battery runs on `main` only (the two pending lanes — `channel-exploration`, `scenario-builder-ux` —
are behind main and incomplete; not in this battery).

**Status legend:** `[ ]` todo · `[~]` running · `[x]` pass · `[!]` fail/blocked
**Run interface:** `python -m ogclews_link run <name>` (`python -m ogclews_link list`); standalone
scripts under `experiments/`. Use the `OG-PHL/.venv` interpreter.
**Pass =** (a) solver converges (SS and/or TPI as tagged), (b) sign/direction correct, (c) magnitude
plausible, (d) matches the golden record once captured.
**Capture per run** (golden record, for regression): `ogclews_link.golden` flattens `Y, C, K, L, r, w`,
the `Y_m` vector (+ pct-diffs) into `results/golden.json` — `golden.save(golden.from_context(name, ctx))`
to establish, `golden.check(...)` to diff a later run. CEV/welfare comes from the viz layer. See
`results/README.md`.

## Scope decisions (pinned)
- **SS-vs-TPI:** SS is used ONLY where safe — the baseline + the param-setting channels
  (`energy_price`/`investment`/`capital_intensity`, which read no OG result arrays), as a fast
  convergence gate. Everything that reads the OG result dict (`discount_rate`, `demand`,
  `clean_incidence`, `carbon`, `health`, `full`) runs **TPI** (canonical; SS crashes on the TPI-shaped
  reads — `Y_m[:, m]`, `r[:10]`, `c_i[:, i_e]`). SS ≈ seconds–1 min; TPI ≈ minutes each — confirm before TPI groups.
- **Golden records:** YES — capture aggregates per run so the battery is repeatable and future changes
  diff against a baseline.
- **Multi-country:** unit-level only for now (**only `ogphl` is installed**); a real multi-country solve
  is deferred until the IDN/ETH/ZAF OG packages are installed.
- **Reproducibility:** baseline solved twice must be identical.

## Running the battery (continuable, small groups)
Driven by `experiments/run_battery.py` — runs the model the **canonical way** (`runtime.build_baseline`
→ `ogcore.execute.runner`, the same `Specifications → runner` flow as
`OG-PHL/examples/run_og_phl_multi_industry.py`), under the **OG-PHL venv**. It runs PHL's **M=4**
energy-isolated aggregation — `[Natural Resources, Electricity(idx 1), Construction/Trade/Services,
Manufacturing]`, with `io_matrix`/`alpha_c` calibrated from the SAM — **not** the example's illustrative
M=2 informal/formal split (np.eye). PHL's calibrations are M=1 (default; channels collapse) and M=4
(used here). One small group per invocation; `results/battery-state.json` is persisted after every item
so it is **fully resumable** — stop after any group and re-run `--next` to continue.

    .../OG-PHL/.venv/bin/python experiments/run_battery.py --status      # progress; runs nothing
                                                ...        --list        # the plan, as items
                                                ...        --next        # run the next pending group
                                                ...        --group NAME  # run one named group
                                                ...        --item ID     # run one item
                                                ...        --next --dry-run   # show; no solves

Groups (small): `foundation → ss_smoke → energy → supply → forward → health → combined`. The hard gate
is **convergence** (solve returns / exit 0); signs & magnitudes are recorded to the golden baseline for
review. The OG-PHL **baseline is identical across all tests** (only the reform changes), so it is solved
**once** — at TPI, which produces both the SS and TPI baseline solutions — into the standard OG baseline
dir, and every reform points `baseline_dir` at it and reads it **from disk** (exactly how a user runs a
reform); only the reform is solved. `foundation` establishes it; later items reuse it (on disk, so reuse
survives across invocations). The TPI groups (energy, supply, forward, health, combined) are the slow ones.

---

## Part 0 — Foundation (run first; everything compares to it)
- [ ] Unit/transform suite green — `pytest tests/` (expect **69 pass / 1 skip**)
- [ ] Baseline **SS** solves clean (no aggregate-resource-constraint failure)
- [ ] Baseline **TPI** solves clean
- [ ] Baseline reproducible (solve twice → identical aggregates)
- [ ] Signal readers parse the real CLEWS dirs (`Base_v9`/`PEP_v9`): emissions (ByMode + plain), capex,
      cost-index, the **EBb4 dual**, `capital_intensity_ratio` — sentinels (999999) zeroed, species
      filtered, year-overlap non-empty

---

## Part 1 — Each part individually

### 1. energy_price (CLEWS→OG)
- [ ] SS — Route A, controlled +20% — `run energy_price` — demand falls; converges
- [ ] SS — Route A, **dual** source (EBb4 shadow price) — uses the real LP dual; sign right
- [ ] TPI — `clean_incidence` (recycle + `energy_cmin`) — `run clean_incidence` — textbook **regressive**
      incidence over the path; guard: `energy_cmin` below every group's baseline energy use
- [ ] SS — Route B cost-push **Z-haircut** — `python experiments/run_io_calibrated_energy_shock.py` —
      **LOWERS GDP** (resource cost); electricity-only vs energy+fuels carrier
- [ ] SS — **sub-good targeting** (electricity vs water) via the discovered `Concordance` — shock lands
      on the right industry column with the expected dilution (real-solve check of `aggregation.py`)

### 2. investment — public infra (CLEWS→OG)
- [ ] TPI — `alpha_I`→K_g — `run investment` (NB PHL grid-capex Δ≈0; also run with a forced non-trivial
      `scale` to exercise the mechanism) — K_g/GDP move the right way; converges

### 3. capital_intensity — private generation γ (CLEWS→OG)  ⚠ highest-priority untested
- [ ] SS — **crowding-out** — `python experiments/run_capital_intensity.py` — energy K↑, other K↓,
      cost-of-capital↑ emerge endogenously (the deferred open item)
- [ ] SS — also `run capital_intensity` (channel path, γ from `capital_intensity_ratio`)
- [ ] SS — ITC "view" — `python experiments/run_energy_itc.py` — consistent with the γ view
      (the "three views of generation capex: γ / cost-push Z / ITC — pick one")

### 4. carbon (both directions)
- [ ] TPI — `tau_c` recycled & not — `run carbon` — converges; revenue/recycling consistent (recycle reads the base → TPI)
- [ ] SS — **absurd-`tau_c` hard-block fires** (guard test); deflator correct
- [ ] CLEWS penalty side applied correctly

### 5. discount_rate (OG→CLEWS)
- [ ] TPI — `run discount_rate` (standalone) — OG rate → CLEWS `DiscountRate` **emitted in
      CLEWS-consumable format**; value sensible. **Must be TPI** (reads the rate path). Reform delta in `forward`/`full`.

### 6. health (CLEWS→OG)  ⚠ most likely to hit solver trouble (RC_SS Walras residual)
- [ ] TPI — `run health` — `disease_pop`, **deaths-added** direction converges; mortality/productivity sign right
- [ ] TPI — **lives-saved / cleaner-air** direction (negative target) — `experiments/test_health_bidirectional.py`
      — converges with the scoped RC_SS gate; realized SS |RC| within gate
- [ ] GBD PM2.5 burden ingestion — deaths + YLD morbidity by age feed h(s)/g(s) — `validate_health.py`

### 7. demand (OG→CLEWS)
- [ ] TPI — `run demand` (standalone) — OG `Y_m` → CLEWS demand scaling **emitted in
      CLEWS-consumable format** (producer side). **Must be TPI** (reads the `Y_m` path); inert ≈1 standalone.

---

## Part 2 — All together
- [ ] SS — `run full` (smoke: does the full stack converge at SS?)
- [ ] TPI — `run full` — CLEWS→OG (price, investment, health) + OG→CLEWS (discount, demand) + carbon;
      sensible aggregates
- [ ] TPI — `ACROSS_STEPS` cumulative — `python experiments/run_across_steps.py` — each layered channel's
      marginal contribution adds up; solver survives the full stack

---

## Cross-cutting / "what else" (not covered by per-channel + combined)
- [ ] **Loop closure / both directions** — the OG→CLEWS outputs (discount_rate, demand) are not just
      produced but in the exact format CLEWS ingests
- [ ] **Revenue recycling** — `recycle_via_transfers` (the `alpha_T ≥ 0` floor fires), `route_revenue`
      for each destination; revenue-neutrality where claimed
- [ ] **Units / currency bridge** — `deflator`, `%GDP` via `gdp_musd`, MUSD↔numeraire; a wrong-unit input
      is caught (carbon hard-block is one such guard)
- [ ] **Guards & failure modes fail loudly** — `energy_cmin` too high breaks the solve, RC_SS gate,
      negative `alpha_T` floor, M=1 resource-targeting error
- [ ] **Signal robustness** — both CLEWS CSV layouts (pivot "Sum of…" + long), missing-file handling,
      ByMode-vs-plain emissions, EBb4 dual un-discounting, **year alignment** (`og_start_year` vs CLEWS years)
- [ ] **Viz/report on real output** — `python -m ogclews_link.viz` end-to-end on an actual coupled run
      (deck + index.html render; titles derived-not-asserted)
- [ ] **Reproducibility** — same scenario twice → identical (also Part 0)
- [ ] **Multi-country (deferred)** — unit-level cross-country (IDN/ETH/ZAF SAMs) already passes; real
      solve requires installing those OG packages

---

## Run-early risks
1. **capital_intensity crowding-out SS solve** — the single most important *untested* thing.
2. **health bidirectional solve** — most likely to hit the RC_SS Walras residual.

Run these two before the combined runs so surprises surface early.

## Compute notes
- SS solves: fast (seconds–~1 min). TPI: minutes each — this is the batch to confirm before launching.
- Solves use a dask client (`num_workers`); SS-only via `time_path=False`.
- Output dirs are per-run; never write to the shared CLEWS run dirs.
