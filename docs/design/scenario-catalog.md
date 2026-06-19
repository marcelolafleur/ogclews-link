# The scenario catalog — schema, lineage, and how the doors consume it

**Status:** prototype built (branch `scenario-builder-ux`). **Artifacts:** `docs/design/scenario_catalog.yaml`
(authored source) → `ogclews_link/scenario_catalog.json` (generated, loaded), `ogclews_link/scenario_catalog.py`
(loader + validator), `tests/test_scenario_catalog.py` (14 tests, incl. anti-drift checks). **Builds on:** `scenario-creation-ux.md` (the three-doors UX) and
`scenario-builder-and-policy-levers.md` (the backend seam — this catalog is the machine-readable form of
that note's prose "choice catalog").

## Why a catalog at all

All three doors (template gallery, guided builder, expert config) need the same facts about every lever:
its label, what it does, type, default, valid range or choices, units, which options conflict, and which
tier (core vs advanced). Today those facts live only in the `apply()` signatures and `validate()` methods
of `channels.py` / `policy_levers.py` — readable by a Python author, invisible to a UI. The catalog
promotes them to one declarative file that every door reads. It is the single highest-leverage artifact
for the builder, and it is mostly transcription of what already exists.

## Schema — borrowed from ParamTools, with three additions

We deliberately reuse the **ParamTools / PSL** field vocabulary so the file is recognizable to OG-Core and
Tax-Calculator developers (those projects define every model parameter this way). ParamTools' per-parameter
fields are `title`, `description`, `notes`, `type` (`int`/`float`/`bool`/`str`/`date`), `number_dims`, the
default (`value`), and `validators` — `range` `{min, max, level}` and `choice` `{choices}`. PSL's universal
UI-grouping convention is a `section_1` / `section_2` pair declared under the schema's `additional_members`.

What each catalog option carries, and where it comes from:

| Field | Source | Notes |
|---|---|---|
| `title` | ParamTools | form label |
| `description` | ParamTools | plain-language help; the "why it matters" |
| `notes` | ParamTools | caveats / citations |
| `type` | ParamTools | `int`/`float`/`bool`/`str`/`list`/`industry_ref` |
| `default` | ParamTools `value` | **mirrors the `apply()` signature** (see drift note below) |
| `validators.range` | ParamTools | `{min, max, level}`; `level: warn` = soft bound, not a hard stop |
| `validators.choice` | ParamTools | enums (e.g. `price_source`) |
| `unit` | **added** (PolicyEngine-style) | `"/1"` (ratio), `currency-USD`, … — ParamTools has no native unit |
| `tier` | **added** | `core` \| `advanced` — drives progressive disclosure (door 2's "Show advanced") |
| `depends_on` / `conflicts_with` | **added** | conditional visibility + cross-option conflicts; ParamTools' `validators.when` only does conditional *validation*, not *visibility* |

Two deliberate departures from a literal ParamTools file:

- **Hierarchical, not flat.** ParamTools (and PolicyEngine) put every parameter at the top level —
  PolicyEngine even uses dotted paths (`gov.irs.credits.ctc.amount`) to get a folder tree for free across
  ~111,000 parameters. We have **6 channels + 2 levers**, and the door-2 mental model is "toggle a channel,
  then set its options." So the catalog nests `channels → options`. It is ParamTools-*inspired*, not a
  drop-in ParamTools defaults file. (If we ever want server-side validation for free, flattening to real
  ParamTools is mechanical — the field names already match.)
- **`default:` scalar, not `value: [{"value": x}]`.** ParamTools wraps every default in a labeled-record
  list to support dimensioned values. Our options are scalars/enums, so the plain form is far more
  readable; we adopt the record form only if an option ever needs to vary by year/region.

> The `schema.additional_members` block in the catalog is a sketch; **this table is the authoritative
> field list.** Channel-level fields (`direction`, `theory_status`, `post_solve`, `status_note`,
> `conflicts_with`) and the template/guardrail fields are documented here.

## The one real decision: a single source of truth for defaults

A catalog that *duplicates* the defaults from the `apply()` signatures creates two sources of truth that
will drift — someone changes `shock=0.20` to `0.15` in code and the UI keeps offering `0.20`. Three ways
to handle it, in order of preference:

1. **Introspect the signatures (recommended).** Read defaults and types straight from the `apply()`
   signatures (`inspect.signature`) at load time; the catalog supplies only the *human* metadata
   (label, description, unit, range, tier, conflicts) that code can't express. Code stays the single
   source of truth for defaults; the catalog can't drift on them because it doesn't store them.
2. **Catalog is the source of truth.** Channels read their defaults *from* the catalog. Cleaner long-term
   but a bigger change to the channels.
3. **Duplicate + a sync test.** Keep both (as the YAML does now) and add a CI test asserting
   `catalog.default == signature.default` for every option. Lowest effort, catches drift late.

The catalog ships as (3): defaults are duplicated, and `test_catalog_defaults_match_signatures` asserts
they equal the `apply()` signatures in both directions, so they cannot silently drift. The recommendation
is still to move to (1) when this is productionized.

(Authored as `docs/design/scenario_catalog.yaml`; the loader reads the generated
`ogclews_link/scenario_catalog.json` — regenerate on change, and `test_json_matches_yaml` guards it.
JSON keeps the loader stdlib-only, matching how OG-Core/Tax-Calculator ship their ParamTools catalogs.
This note is the human narrative.)

## How each door consumes the catalog

- **Door 1 — template gallery** reads `templates`: each is a question-framed, pre-assembled
  `[(channel, options)]` (plus a `run_mode`: `single` / `layered` / `compare_set`). One click → view
  precomputed results, or fork into door 2 with everything pre-filled. Each template also carries usage
  metadata — `reads_clews` / `emits_clews` / `requires` / `direction` / `notes` — documenting the real
  coupling (what it reads from CLEWS, and which OG→CLEWS artifacts feed back only on a CLEWS re-solve).
  `experiments.py` derives `EXPERIMENTS` / `ACROSS_STEPS` from these, so the catalog is the single source
  for templates too (guarded by `test_experiments_match_catalog`).
- **Door 2 — guided builder** reads `channels` + `levers`: render a card per channel; for each enabled
  channel show its `tier: core` options inline (default-filled), `advanced` collapsed; disable options
  whose `depends_on` is unmet and targets that fail `separability`; run `guardrails` as pure validation on
  every edit and show the baseline diff. **No solve.**
- **Door 3 — expert/config** needs no catalog rendering — it edits the resulting `Experiment` JSON / calls
  the CLI — but it can use the catalog's `validators` and `guardrails` to lint a hand-written scenario
  before a run.

The point is that all three emit the *same* object — the existing `Experiment(name, [(channel, options)], …)`
— so a template (door 1) opens in the builder (door 2) opens in the config (door 3) with no conversion.

## Scenario as a shareable object — the PolicyEngine lesson

PolicyEngine's most copyable idea isn't its UI, it's its **encoding**: a reform is a small dict
(`{parameter_path: {"start.end": value}}`) stored server-side under a numeric **policy id** with a
**hash** that dedupes identical reforms; the baseline is just another id (`baseline=2` = current law), so
**reform-vs-reform comparison needs no special mode** — you point `baseline` at another scenario. The
whole reform travels in a URL.

Mapped to us, with almost everything already in place:

- **A scenario already is that small object** — the `Experiment` (`[(channel, options)]`). Give it a
  content **hash** (dedupe + cache key for the precomputed gallery) and a stable **id/slug**. That id is
  the shareable handle and the cache key for "has this been solved already."
- **Baseline = the current calibration** (our "current law"). Comparing two scenarios = running each
  against that baseline and diffing — exactly today's baseline-vs-reform, generalized so the "baseline"
  can itself be another scenario id (reform-vs-reform).
- **The provenance manifest we already emit (`ogclews_manifest.json`) is the reproducibility record** —
  it should carry the scenario id/hash + catalog version so a result is always traceable to the exact
  levers and defaults that produced it.
- **What we adopt vs skip:** adopt the *id + hash + baseline-is-just-an-id* model. Skip the per-parameter
  date-range keying (`"2024-01-01.2100-12-31"`) — our channels already own the time profile internally
  (phase-in, persist, SS-tail), so a flat options dict is the right granularity for us.

## Smallest slice to wire it in

1. A **loader + validator** — **built**: `scenario_catalog.py` parses the JSON and exposes
   `validate_scenario()` — option type/range/choice plus the `guardrails` as pure predicates, returning
   errors / warnings / infos over a candidate `[(lever, options)]`. Door 2's engine and door 3's linter;
   no solve.
2. Move defaults to **option (1) introspection** + drop the duplicated `default:` values (or keep them and
   add the sync test).
3. Formalize `templates` as the gallery loader and add the **scenario id/hash**.
4. Then build door 1 (gallery) — it ships value fastest (needs only templates + cached results) — then
   door 2 (builder).

MUIOGO renders doors 1–2 from this file and shells out to the existing CLI for the run. Nothing here needs
new solve machinery.
