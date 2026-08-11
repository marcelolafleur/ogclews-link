# Drafts: upstream reports for the ogcore 0.19.1 payroll double count

Not posted anywhere. Both drafts below are ready for review; posting needs your
go-ahead (and would come from your account).

---

## Draft 1 — OG-Core issue

**Title:** v0.19.1 double counts payroll tax revenue when tau_payroll != 0, breaking the steady-state resource constraint

**Body:**

PR #1184 adds `payroll_tax_revenue` into `iit_payroll_tax_revenue` in
`aggregates.revenue`:

```python
if np.any(p.tau_payroll != 0):
    iit_payroll_tax_revenue += payroll_tax_revenue
```

But the household tax liability already includes the explicit payroll tax:
`tax.income_tax_liab` returns `T_I + T_P`, where `T_P = tau_payroll * labor_income`,
and `iit_payroll_tax_revenue` is the aggregation of that liability. So the
payroll take was in total revenue all along, and the new line counts it a
second time. The comment above the added block ("payroll taxes ... are
excluded from the income and payroll tax functions") doesn't match what
`tax.py` does.

The consequence is government revenue that no household paid — phantom revenue
of `tau_payroll` times labor's share of GDP. The budget rule spends it, and the
steady-state aggregate resource constraint fails by exactly that amount. On
OG-PHL's calibration (`tau_payroll = 0.0675`, SSC collections of 2.78% of GDP)
the RC residual is -0.0808 with model output Y = 2.9, and 0.0278 x 2.9 = 0.0806.
The residual is identical from any solver starting point, which is what you'd
expect from an identity violation rather than a convergence failure.

Reproduce: solve any baseline with a nonzero `tau_payroll` under v0.19.1
(`RuntimeError: Steady state aggregate resource constraint not satisfied`);
the same JSON solves under v0.19.0. OG-USA is unaffected because it runs
`tau_payroll = 0`.

The pre-#1184 code was already correct on the total:
`iit_revenue = iit_payroll_tax_revenue - payroll_tax_revenue` was a reporting
split, not a sign that revenue was missing. #1184's improvement to how
`payroll_tax_revenue` itself is measured (`tau_payroll * w * L` when explicit,
`frac_tax_payroll` otherwise) is good and worth keeping — it's only the `+=`
that needs reverting. Happy to open a PR.

---

## Draft 2 — comment on EAPD-DRB/OG-PHL #85

Heads-up: this PR's packaged parameters now fail to solve under ogcore
v0.19.1 (`RuntimeError: Steady state aggregate resource constraint not
satisfied`, RC residual -0.081). Nothing wrong with the calibration — 0.19.1
double counts payroll tax revenue when `tau_payroll != 0`
(PSLmodels/OG-Core#NNNN), and this is the first calibration in the family with
an explicit payroll rate, so it's the first to hit it. Solves fine under
0.19.0 + #1189, or under 0.19.1 with the double-count line reverted.

---

*(NNNN = the issue number once Draft 1 is filed.)*
