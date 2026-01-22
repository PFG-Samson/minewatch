# MineWatch — Investor Proposal

## Executive summary
Mining operations are required to monitor environmental impact, land disturbance, and compliance with lease boundaries. Today this is often done through manual GIS workflows, expensive consultants, and slow reporting cycles.

**MineWatch** is a lightweight monitoring platform that automatically ingests defensible satellite data and produces **clear change insights, alerts, and compliance-ready reports**—without waiting for field reports.

---

## The problem
Mining companies and regulators repeatedly need to answer:

- What changed since the last reporting period?
- How much vegetation was lost or recovered?
- Did disturbance expand beyond approved boundaries?
- Can we produce an audit-ready report quickly?

Current reality:

- manual GIS processing
- inconsistent baselines
- delayed visibility
- high cost per report

---

## The solution (MineWatch)
MineWatch continuously monitors an “area of truth” around a mining lease:

- store mine boundary and buffer zone
- automatically ingest satellite scenes (Sentinel‑2; Landsat optional)
- compute repeatable vegetation and disturbance change metrics
- surface hotspots on an interactive map
- trigger simple rule-based alerts
- generate PDF reports in minutes

The product is intentionally focused: **reliable, repeatable analysis that supports compliance and ESG reporting**.

---

## Product today (current build)
This repository already includes:

- Web dashboard with interactive map
- Mine boundary setup (GeoJSON)
- Satellite metadata ingestion via STAC (Sentinel‑2 L2A)
- Persisted analysis runs + results storage
- Alert list + report generation (PDF)

Near-term enhancement:

- replace placeholder change zones with **real NDVI change detection**

---

## Why this wins
- **Defensible data:** Sentinel‑2 is free, widely accepted, and auditable.
- **Operational simplicity:** minimal workflow; no GIS expert required for day-to-day use.
- **Fast reporting:** produce a compliance-friendly report quickly.
- **Expandable platform:** same pipeline supports rehabilitation tracking, multi-mine portfolio views, and regulator portals.

---

## Target users
- Environmental Officer / ESG team
- Mine Manager / Operations
- Compliance & Audit
- Regulators / external auditors (read-only, evidence-focused)

---

## Market opportunity
Mining compliance and ESG reporting is a recurring spend:

- internal teams + consultants
- repeated quarterly/annual reporting
- increasing scrutiny from regulators and investors

MineWatch is positioned as a **cost-reducing, risk-reducing** tool with clear ROI:

- fewer consultant hours
- faster incident detection
- better audit readiness

---

## Business model
Suggested pricing (can be validated via pilots):

- **Per mine / per month** subscription
- optional add-ons:
  - higher frequency monitoring
  - multi-site portfolio dashboard
  - regulator sharing portal
  - custom reporting templates

---

## Go-to-market (practical)
1) Pilot with 1–3 mines (friendly customers)
2) Prove value via:
   - faster reporting
   - reduced GIS workload
   - evidence for compliance
3) Expand within the operator (more mines)
4) Partnerships:
   - environmental consultancies
   - ESG platforms

---

## Roadmap (focused)

### Phase 1 (MVP hardening)
- automated STAC ingestion on schedule
- real NDVI change detection + vectorized zones
- threshold-based alerts
- improved report templates

### Phase 2 (Scale)
- multi-mine portfolio
- role-based access / regulator read-only links
- imagery layer visualization improvements

### Phase 3 (Future options)
- SAR deformation monitoring (subsidence)
- ML-based land cover classification
- API for regulators

---

## Competitive landscape
Alternatives include:

- manual GIS workflows
- consultant reports
- broad “environmental platforms” that are heavy and expensive

MineWatch differentiates by being:

- focused on a specific, high-value monitoring workflow
- transparent and auditable
- operationally simple

---

## What we’re raising / asking for
Seeking support for:

- product hardening (NDVI pipeline + automated scheduling)
- pilot deployments with operators
- UI/UX polish and reporting templates
- security and multi-tenant hosting

---

## Contact / next step
If you’re interested in a pilot or investment discussion:

- Request a demo walkthrough
- Provide a mine boundary to run an example monitoring cycle
