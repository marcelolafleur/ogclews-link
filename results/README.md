# results/ — golden regression records for the test battery

`golden.json` is the **committed baseline**: a `{ run-name -> record }` table of key OG-Core
macro aggregates (`Y, C, K, L, r, w, Y_m`) captured from each test run via
`ogclews_link.golden`. It does not exist until the first battery run establishes it — capture,
then commit `golden.json`, and every later run diffs against it.

Usage (after a coupled run yields an `ExperimentContext` `ctx`):

```python
from ogclews_link import golden

# establish / update the baseline, then `git add results/golden.json`:
golden.save(golden.from_context("energy_price", ctx))

# or check a fresh run against the committed baseline:
r = golden.check("energy_price", ctx.base_tpi, ctx.reform_tpi)
assert r["match"] in (True, None)        # None = no baseline captured yet
if r["match"] is False:
    print(r["diffs"])                    # {dotted_key: (golden, current)}
```

SS values are recorded as scalars; TPI values as `t0 / ~10y / SS`. CEV/welfare is captured by
the viz/report layer (`python -m ogclews_link.viz`), not here.
