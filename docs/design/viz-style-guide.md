# Visualization style guide

**Goal.** One house style for every figure the coupled model emits, so the deck reads as a single
publication — honest by construction, colourblind-safe by default, and legible when any figure is
lifted out on its own.

**Status:** living spec. Most of §3–§5 is already implemented in `ogclews_link/viz/style.py`; §6's
caption discipline and §7's annotation layer are partly built; §8's mechanism layer is aspirational.
The last column of §10 tracks what still needs building.

**Audience:** anyone adding or editing a figure in `ogclews_link/viz/`.

**Sources.** Adapted to a deterministic macro–energy model deck from three published house styles:
the **Financial Times** (its open-source [`o-colors`](https://github.com/Financial-Times/o-colors),
[`g-chartframe`](https://github.com/Financial-Times/g-chartframe), and
[Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary)),
**Nature / _Nature Methods_** (figure guidelines + the Wong / Okabe–Ito colourblind-safe palette),
and **Quanta Magazine's** art direction. Full links in §11.

---

## 1. The one rule — honest by construction

A figure **describes what is plotted; it never asserts a conclusion.** Direction and magnitude appear
only as **computed numbers** (read off the data), never as judgment words. This is not just our
preference — it is Nature's own caption rule: a legend gives *"a short statement of what is depicted
in the figure, **not the results**"* and must be *"understood in isolation from the main text"*
(Nature, Brief guide to submission).

Concretely:

- **Titles are neutral descriptions.** "Interest rate and wage over the transition", not "Rates climb".
  The scenario/country identity rides in the title text, the run directory, and the source credit —
  so the *style* stays country- and model-generic.
- **Numbers, not verdicts.** `+0.24%` on an annotation is fine; "a strong gain" is not. Any
  direction/magnitude word must be *derived* from the plotted value, never hardcoded — see the wording
  note in `style.py`.
- **Point estimates from one deterministic solve.** There are no error bars to hide behind, so the
  caveat is explicit: where a run uses a stand-in input, the figure carries the illustrative caption
  (the `illustrative` / `--calibrated` switch), and the source line always names the model.
- **Axis integrity.** Magnitude/bar charts start at zero (FT Visual Vocabulary: *"column … must start
  at zero"*); deviation charts pivot on an explicit reference line; never truncate an axis to
  exaggerate a move; choropleths map rates, not totals.

Everything below serves this rule.

---

## 2. Three modes, three jobs

FT, Nature, and Quanta are **not three looks to blend into one** — they are three jobs. Give each
figure the mode that fits *its* job, and don't apply one where another belongs.

- **FT mode — the results / editorial layer.** One idea per chart, direct labels instead of legends,
  a grey context with a single accent on the series in focus, and a *guiding annotation layer*.
- **Nature mode — the evidence / detail layer, and caption discipline.** Dense multi-panel figures,
  a colourblind-safe palette, and self-contained captions. This is where rigor lives.
- **Quanta mode — the mechanism layer.** Bespoke, progressively-disclosed, *honestly-schematic*
  diagrams that make an invisible mechanism graspable. Quanta's whole art direction exists to
  "visualize invisible things" — which is precisely our problem (the coupling, the dual, the wedge).

| Deck section | Mode | Example figures |
|---|---|---|
| Headline | **FT** | `headline_dashboard`, `across_steps_waterfall`, `summary_table` |
| Macro & fiscal | **FT** | `macro_transition`, `fiscal_transition`, `revenue_transition`, `rates_transition`, `public_investment` |
| Welfare | **FT** | `cev_by_group`, `cev_decomposition`, `cev_by_age` |
| Distribution | **FT** | `energy_demand_by_group`, `consumption_by_age`, `asset_by_age`, `income_composition_by_age` |
| Composition (GE structure) | **Nature** | `consumption_by_good`, `sectoral_reallocation`, `consumption_by_good_by_group` |
| Health | **Nature** | `gbd_age_profiles`, `mortality_by_age`, `morbidity_by_age`, `demographic_transition_by_age` |
| OG-Core native suite | **Nature** | `og_default_outputs` (the ~31 canonical plots) |
| How the scenario is built | **Quanta** | `clews_signal_vs_applied`, `channel_inputs_over_time`, `capex_by_technology`, `energy_physical`; the coupling / 8-channel explainer (to build) |

The caption discipline of §6 applies to **every** mode.

---

## 3. Palette (colourblind-safe, committed)

**Rule: colourblind-safe by construction, not by inspection.** Every default below survives
deuteranopia/protanopia; only *custom* colours need a CVD check.

**Unordered categories (sectors, goods) — the Okabe–Ito / Wong 8** (Wong 2011, _Nature Methods_; the
scientific standard). Use a **fixed order** so it is never re-decided per chart (the FT discipline):

| # | name | hex |
|---|---|---|
| 1 | blue | `#0072B2` |
| 2 | vermillion | `#D55E00` |
| 3 | bluish green | `#009E73` |
| 4 | orange | `#E69F00` |
| 5 | sky blue | `#56B4E9` |
| 6 | reddish purple | `#CC79A7` |
| 7 | amber (yellow `#F0E442` reads poorly on white) | `#F5C710` |
| 8 | neutral grey | `#999999` |

**Signed data (gains vs losses) — diverging RdBu poles**, centred on a neutral zero: loss `#B2182B`,
gain `#2166AC`, neutral `#F7F7F7`. CVD-safe, and deliberately **not** traffic-light red/green.

**Ordered categories (income groups, poorest→richest) — a single-hue sequential blue ramp**
(`#C6DBEF → #08306B`). Perceptually ordered; dark = more. This is also the FT tonal-ramp approach.

**Grey context + one accent (the FT highlight system).** Colour only the series in focus; fade the
rest to grey. *"A line of red in a sea of grey lines will immediately stand out; if every line is a
different colour, nothing stands out."* Greys: ink `#222`, secondary `#555`, muted `#888`, grid
`#E6E6E6`, frame/zero `#333`.

**Brand accents (the kicker rule, single-series highlight) — the FT triplet:** claret `#990F3D`,
oxford `#0F5499`, teal `#0D7680`. These are the *verbatim* FT `o-colors` brand hexes, and we already
use them.

**Background: white.** Nature-aligned, portable (print, screen, and Artifact CSP), and it doesn't
constrain colour lightness the way a tinted ground does. FT's signature `paper #fff1e5` is a *brand*
choice we deliberately don't adopt; it's available if we ever want a distinctive house ground.

> **Reconcile (code change):** today's `style.CATEGORICAL` is only partly Okabe–Ito (it mixes in an
> Economist red and an oxford blue). Move the **sector/goods** cycle to the canonical 8 above so it is
> CVD-safe by construction; keep claret/oxford/teal for *kickers and highlights*, and RdBu for signed.

---

## 4. Typography & layout

**Sans for all chart furniture.** FT uses MetricWeb for every chart; Nature specifies Arial/Helvetica.
We use `Source Sans 3 → Inter → Roboto → DejaVu Sans` (installs cleanly, degrades safely). **Serif is
for editorial headlines only** — reserve an optional serif display (the Quanta / FT-Financier signal
of "serious journalism") for the deck cover and mechanism explainers, not for data furniture.

**Hierarchy (the FT `g-chartframe` pattern), driven by `style.title_block`:**

| element | role | treatment |
|---|---|---|
| kicker | category tag | small UPPERCASE, coloured rule + accent (claret/oxford/teal) |
| title | what is plotted | largest, near-black `#222`, regular/​semibold weight |
| dek (subtitle) | metric · units · horizon · the computed number | ~85% of title size, warm grey `#555` |
| source | model credit + caveats | ~55–60% of title size, muted grey `#888` |

**Sizes.** Our screen/deck sizes (title ~15pt, dek ~11pt, source ~8pt) are right for on-screen viewing.
For any **print/paper** figure, meet Nature: text ≥ 7pt, panel labels 8pt **bold lowercase** `a b c`,
line weights ≥ 0.25pt, single-column 89 mm / double 183 mm, ≥ 300 dpi RGB. (We save screen figures at
200 dpi; bump to 300 for print output.)

**Chrome (Tufte + FT).** Open frame — top/right spines off; left spine only when it aids reading.
**Horizontal y-gridlines only**, faint, behind the data; no vertical grid; no tick marks — the grid
carries the scale. All in `style.apply()` / `style.clean()`.

---

## 5. Labelling & the annotation layer

This is where FT most outperforms a default chart, and where we have the most to add.

- **Direct labels over legends.** Put the series name at the end of its line, in the series colour —
  it kills the legend box and the reader never looks away from the data. `style.label_ends` does this
  (with collision-nudging).
- **Grey context, colour signal.** Only the focus series is coloured; the rest are grey (§3).
- **The annotation layer (to build out).** Mark the events and inflections that orient the reader:
  the closure-rule year (we mark it), the peak, the value on the line, the period in focus. Reader
  testing behind FT's work found charts with *"a strong … title and multiple explanatory
  annotations"* performed best.
- **Neutrality constraint on annotations.** Annotate the **event** and the **number**, never the
  verdict. "Budget rule begins (2046)" and "peak +0.24% (2029)" are fine; "growth takes off" is not.

> **Helpers to add** to `style.py`: `mark_event(ax, x, label)` (generalise the retirement/closure
> marker), `shade_span(ax, x0, x1, label)` (highlight a period), and on-line value labels.

---

## 6. Titles & captions — the neutrality resolution

**The tension.** FT favours an *assertive, narrative* title that states the takeaway. Nature requires a
*descriptive* one that states what is depicted, not the result. Our rule sides with Nature — but FT's
instinct to *guide the reader* is right, so we relocate it rather than discard it.

**Resolution — separate _orient_ from _conclude_:**

1. **Title = neutral description** of what's plotted.
2. **Dek = the metric, units, horizon, and the magnitude _as a number_** — e.g. *"% deviation from
   baseline, 2026–2035; peak +0.24% in 2029."* This carries FT's "what/how much" without a verdict.
3. **Annotation layer = FT's guided reading, kept neutral** (§5): mark the event and the value.

That gives FT's guidance with Nature's honesty.

**Self-contained caption (Nature).** A figure's title + dek + source must let it **stand alone**: what
is shown, the units, the horizon, the scenario/run, the source, and the illustrative caveat when
applicable. Keep it under ~250 words; describe *what is shown*, not the method. The credit line is
model-generic — `"OG-Core × CLEWS coupled model · author's calculations"` + any methodology caveat +
the per-run caveat — assembled by `style.source_line`.

---

## 7. Colour-encoding rules (quick reference)

| the data is… | encode with | never |
|---|---|---|
| signed (gain/loss) | diverging RdBu poles by sign | traffic-light red/green |
| ordered (income groups) | single-hue sequential ramp, dark = more | a rainbow |
| unordered (sectors, goods) | the Okabe–Ito 8, fixed order | more than ~8 categories at once |
| one series vs context | one accent on grey | a different colour per series |
| missing / unhighlighted | grey | an attention colour |

Every default here is CVD-safe. Verify any custom colour against a colourblindness simulation before
it ships.

---

## 8. The mechanism layer (Quanta)

**Job:** make an *invisible mechanism* graspable — the CLEWS→OG coupling, the electricity dual, the
consumption wedge, the eight channels. These are exactly the "theoretical and/or entirely invisible"
subjects Quanta's art direction was built for. Its success metric is **internalisation**: a good
diagram lets the reader *own* the idea.

**Principles:**

- **One mechanism per diagram.** Don't cram the whole coupling into one picture.
- **Progressive disclosure.** Build from a simple base; reveal one step at a time. This is Quanta's
  core explanatory move.
- **Motion shows transformation, not spectacle.** Animate a state change; don't animate for flourish.
  Interactive where the reader *exploring* helps ("a picture becomes an experience").
- **Honestly a schematic.** Beauty is instrumental — Quanta is explicit that its images
  *"tell a story … not necessarily [make] realistic representations."* So label mechanism diagrams as
  schematics, and keep every quantitative claim in the data figures (§2 FT/Nature). Expressive is
  fine; **false precision is not** — that's §1 applied to pictures.
- **Use _our_ palette, not Quanta's.** Quanta's site colours are mostly WordPress defaults; the only
  real brand signal is an orange accent on near-black. Borrow the *method*, not the colours.

**Where it lives:** the interactive `index.html` / report, plus a small number (2–3) of hero
explainers. Spend the illustration budget only on the mechanisms that are genuinely hard to explain in
words — not on every figure.

---

## 9. Pre-ship checklist

A figure is ready when:

- [ ] The **title describes what is plotted** — no judgment or direction words.
- [ ] Direction/magnitude appears **only as a computed number**.
- [ ] Colours are **CVD-safe** (defaults are; any custom colour verified).
- [ ] Series are **direct-labelled**; no legend box unless truly unavoidable.
- [ ] If there's a focus series, it's **one accent on grey context**.
- [ ] The **axis is honest** (zero baseline for magnitude; explicit reference for deviation; no
      misleading truncation).
- [ ] The **source line names the model**; the illustrative caveat is present when the run is a stand-in.
- [ ] Title + dek make the figure **stand alone** (units, horizon, scenario).
- [ ] Any **mechanism diagram is labelled a schematic** — no false precision.

---

## 10. Guide ↔ code

The style layer is `ogclews_link/viz/style.py`; every rule above maps to a helper or constant so the
guide and the code can't drift.

| rule | enforced by | status |
|---|---|---|
| theme, typography, greys, chrome | `style.apply()`, `clean()`, `INK/SUB/MUTE/GRID/EDGE` | done |
| title / dek / source / kicker hierarchy (§4, §6) | `title_block` | done |
| CVD categorical for sectors (§3) | `CATEGORICAL` | **reconcile to Okabe–Ito 8** |
| diverging by sign (§3, §7) | `LOSS/GAIN/NEUTRAL`, `signed()` | done |
| sequential income ramp (§3, §7) | `SEQUENTIAL` | done |
| direct end-labels (§5) | `label_ends` | done |
| honest zero reference (§1) | `zero_line` | done |
| % deviation formula (§6 dek) | `pct_dev` | done |
| event marker (§5) | `mark_retirement` | **generalise → `mark_event` / `shade_span`** |
| model-generic source credit (§6) | `source_line`, `SRC` | done |
| on-line value labels (§5) | — | **to build** |
| self-contained captions (§6) | convention + the §9 checklist | partial |
| mechanism explainers (§8) | — | **to build** (in `viz/` or the HTML report) |

---

## 11. Sources

- **FT** — palette: [`o-colors` `_palette.scss`](https://github.com/Financial-Times/o-colors/blob/v5.4.0/src/scss/_palette.scss);
  typography & frame anatomy: [`g-chartframe`](https://github.com/Financial-Times/g-chartframe);
  chart-type-by-relationship & zero-baseline rules:
  [Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary);
  categorical ordering / highlight-on-grey / narrative-title practice:
  [Datawrapper](https://www.datawrapper.de/blog/colors-for-data-vis-style-guides) and
  [GIJN on Burn-Murdoch](https://gijn.org/stories/data-visualization-storytelling-tips-john-burn-murdoch/).
- **Nature** — [Brief guide to submission](https://www.nature.com/documents/nature_3a_initial_revised_submissions.pdf)
  (caption rule, figure sizing, fonts, RGB/dpi); colourblind-safe palette: Wong, B. (2011)
  ["Points of view: Color blindness", _Nature Methods_ 8:441](https://www.nature.com/articles/nmeth.1618),
  identical to the Okabe & Ito Color Universal Design set.
- **Quanta** — art-direction philosophy: [Sketchfab interview with AD Olena Shmahalo](https://sketchfab.com/blogs/community/science-spotlight-quanta-magazine/);
  type: [Fonts In Use](https://fontsinuse.com/uses/36718/quanta-magazine-website).
