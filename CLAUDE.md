# Lloyds SME Lead-Scoring Project — Context

_Last updated: 2026-07-10. This file is the project brief for continuing in Claude Code._

## 1. Goal

Group project with **Lloyds** as client. Build a **lead-scoring (propensity) model** that finds
UK **SME** companies likely to need **new lending**, so relationship managers (RMs) can prioritise
who to approach.

- **Scope is LENDING-ONLY** (confirmed 2026-07-06). Do **not** reintroduce merchant services,
  deposits, or other product lines into the goal, label, or caveats.
- Output = a **ranked lead list** (highest propensity first) for RMs, run daily/weekly.

## 2. Data sources

- **Structured — Companies House** (public API): age, SIC/sector, region, accounts, charges,
  officers, PSC. The **workhorse** for this population.
- **Unstructured — GDELT**: news tone + volume, used at **sector / region level** (join by SIC group
  + region), NOT per company. This is the unstructured pillar.
- **NewsAPI: dropped for per-company use.** SMEs are almost never in the news, and name-matching
  returns false positives (e.g. "10 Castlebar Ltd" → unrelated Castlebars). Free tier is also 1-month
  history / non-commercial / 100 req/day. Keep at most as optional shortlist enrichment, not a feature.

## 3. Label (refined 2026-07-06)

A company is **POSITIVE** if **Lloyds or a Lloyds Banking Group subsidiary appears as the charge
lender** (`persons_entitled`): Lloyds Bank plc, Bank of Scotland, Halifax, Lloyds Bank Commercial
Finance, Black Horse, Lex Autolease, LDC, etc. This is a direct "is/was a Lloyds secured-lending
customer" label (better than the old generic "any new charge" proxy, which is kept as fallback).

**Label caveats:**
1. **Entity resolution is critical** — curate a Lloyds-group name list; avoid unrelated "Lloyd's"
   (e.g. Lloyd's of London insurance).
2. **Positive-Unlabeled**, but SMALL under lending-only scope: residual hidden positives only from
   Lloyds lending that leaves no registered charge (unsecured, overdrafts, cards, some asset/invoice
   finance). Note it; no redesign needed.
3. Label matches target well — no merchant-services gap.
4. **Exclude companies already holding a Lloyds charge from the surfaced lead list** (they're existing
   customers). Leads = high-scoring look-alikes **without** a Lloyds charge.
5. Competitor-bank charges = proven secured borrowers who chose elsewhere = poaching targets / signal.

## 4. Dataset size & modelling constraints (updated 2026-07-10)

- **13,500 SME companies, 250 Lloyds-customer positives (~1.85% prevalence)** — supersedes the
  earlier 5,000/76.
- 250 positives ⇒ 10-events-per-feature allows **~20–25 features** (still prefer parsimony).
- **Logistic regression primary** (explainable), gradient boosting as comparator. Deep learning
  ill-suited for tabular this size.
- **Class weighting** balanced ≈ neg/pos ≈ **53** (LogReg `class_weight='balanced'`; XGBoost
  `scale_pos_weight ≈ 53`).
- Repeated stratified k-fold CV. **Evaluate at true ~1.85% prevalence — never accuracy.**

## 5. Features (Companies House)

Point-in-time as of the cutoff. Candidate set (test via ablation):

- **Company age** (from `date_of_creation`) — continuous / bucketed.
- **Size** — prefer a continuous measure (total/net assets from iXBRL) over the coarse
  `accounts.last_accounts.type` ordinal (micro/small/medium).
- **Tangible fixed assets** — collateral base; most goal-aligned financial feature for *secured* lending.
- **Asset growth** (YoY, needs ≥2 filings).
- **Filing punctuality** — start with `accounts.next_accounts.overdue` (dense, current);
  historical `pct_late` / `avg_days_late` from filing history is the stronger version (derive due date
  = period end + 9 months private / 6 public; first-accounts rule = 21/18 months from incorporation).
- **Sector** — SIC collapsed to a few lending-intensity groups (don't one-hot hundreds).
- **Prior non-Lloyds secured borrowing** — presence/count of charges from **non-Lloyds** lenders
  created before the cutoff (proven-borrower look-alike; NOT leakage since Lloyds is the label).
- **Context-media feature** (GDELT sector×region tone_z, volume_z) — see §7.
- **PSC** (reserve): `is_corporate_owned`, PSC count, recent-control-change. Do NOT use individual
  personal attributes (DOB, nationality) — weak + fair-lending risk.

## 6. Leakage & point-in-time rules (critical)

- **Charge fields where Lloyds is the lender = the LABEL, never a feature.** `has_charges` and
  Lloyds-charge-derived fields must be quarantined on the label side.
- **Non-Lloyds** prior charges (before cutoff) ARE allowed as features.
- **Financial data**: use the last accounts filed **before** the cutoff. Keep long-term-debt items off
  the feature set (they can proxy the very borrowing being predicted).
- **SME definition**: filter to `accounts.last_accounts.type` in {micro-entity, small,
  total-exemption-full/small, medium}; exclude `full`/`group` (large), `dormant`; non-PLC; active.

## 7. GDELT sector × region context-media pipeline

Two roles for GDELT:
1. **Context feature** (per company, in training + scoring): weekly **sector × region** media index.
2. **Sector gate** (scoring-time): pick the hot sector each week (high volume + non-negative tone),
   filter the scored population to it.

**The index:**
- Cell = (sector group, UK region). Query = boolean keyword *sets* (sector terms) + region, `sourcecountry:UK`.
- Per cell, per week: **volume** (article count) and **tone** (avg tone).
- **z-score each cell against its OWN trailing 52-week baseline**: `z = (week − mean₅₂w) / std₅₂w`,
  for both tone and volume. Baseline window must end before the current week (point-in-time).
- Join to each firm by (SIC group, region, cutoff week).
- Region is what gives the feature signal **within** a gated single-sector list.

**Practical / cost:**
- BigQuery bills by **bytes scanned** (columns × days), NOT by #cells or #queries. Adding region as a
  `GROUP BY` dimension does NOT multiply cost — do it in ONE aggregated query, never per-cell loops.
- Use the **partitioned table** `gdelt-bq.gdeltv2.gkg_partitioned` + `_PARTITIONTIME` filter.
  ~3.3 GB/week of GKG text columns → 53 weeks ≈ ~174 GB (< 1 TB free tier). Pull once, cache Parquet.
- **DOC API** (free, keyless, rate-limited 1 req/5s) gives tone+volume timelines directly and can
  replace BigQuery entirely if you don't need GKG themes/geolocation.
- **Thin cells**: region split thins each cell; fall back to sector-only z-score where a cell is below
  a min-article floor. Keep regions coarse (~12 UK ITL1 regions, not cities).

## 8. Evaluation

- Static confusion-matrix / PR-AUC is only a **sanity check** (does the model recover the known 250
  positives?). Evaluate at true ~1.85% prevalence, never accuracy.
- **Headline metric = OUT-OF-TIME (temporal) validation**: train on Lloyds charges before a cutoff,
  score everyone as of that date, check whether high-scoring **non-customers** registered a Lloyds
  charge AFTER the cutoff → turns "false positives" into early true positives. Report **temporal
  Precision@K / lift**.
- Also report **within-sector** Precision@K (mirrors the gated deployment); note it's sparse given
  250 positives fragmented across sectors.

## 9. Output

- Ranked lead list → RMs. **Exclude existing Lloyds-charge holders.** The product is the high-scoring
  **non-customers** (look-alike prospects).
- Optional shortlist enrichment (top-K only): connected-entity media (parent/directors/asset) or news.

## 10. Current code state

`API/GDELT.ipynb` is well-developed:
- **Part 1 (DOC API)** — robust client (throttle, exponential backoff, browser UA, `cooldown()`),
  `build_query`, `timeline_tone`, `timeline_volume`, `article_search`.
- **Part 2 (BigQuery)** — `bq_query()` with free dry-run cost guard; Query A (daily tone+volume);
  Query B (UK **region** rollup from `V2Locations`, `CITY_TO_REGION`).
- **Part 3 (BigQuery)** — ALL sectors in one scan; per-sector `tone_z`/`vol_z` vs own baseline;
  per-day volume (partial-week-safe); `MIN_ARTICLES=25`, `MIN_WEEKS=12`; Parquet cache; `DEV_MODE`.
- **Part 4 (BigQuery)** — the §7 sector × region index: ONE query `GROUP BY sector, region, week`
  (`V2Locations` unnest + `CITY_TO_REGION` rollup in SQL, `GKGRECORDID`-deduped); point-in-time
  trailing z per (sector, region, week) cell — every week, not just the latest; thin-cell fallback
  to sector-only z (`MIN_CELL_ARTICLES=10`, `z_source` column); output `media_index`
  (`sector·region·week·articles·tone_z·vol_z·z_source`) cached to `context_media_index_*.parquet`.
  Pandas logic verified on synthetic data; the region-cell BigQuery pull itself not yet run.

Other files: `API/CompaniesHouse/…` (per-company profile/officers/filing/charges/PSC JSON + accounts
PDF); `ch_company_profile.py` (profile reader + `get_filing_history` + `filing_punctuality`);
`gdelt_doc_example.py`; `lloyds_ch_feature_catalog.xlsx` (feature roles + proxy-label definition +
leakage rules).

## 11. Next steps / TODO

- [x] **Wire sector × region together** (2026-07-10, `GDELT.ipynb` Part 4): `GROUP BY sector,
  region, week` + per-cell z-scores + sector-only fallback → the joinable context-media index.
  Remaining: run the pull (`USE_CACHE=False`) to build the region cache, ideally with
  `BASE_WEEKS = 53` for the full 52-week trailing baseline; sanity-check the fallback share.
- [ ] Build the point-in-time company feature table (§5) and the temporal train/test split (§8).
- [ ] iXBRL financial extractor for tangible assets / net assets / employees (pre-cutoff snapshot).
- [ ] Curate the Lloyds-group lender name list for the label (entity resolution).
- [ ] Ablation: does the context-media feature beat the structural features?

## 12. Guardrails recap

- Lending-only scope. Lloyds-charge = label (leakage). Point-in-time everything. Exclude existing
  customers from leads. Evaluate temporally at true prevalence. Keep models simple / parsimonious.
