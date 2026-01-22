# About MineWatch

## What is MineWatch?
MineWatch is a monitoring tool for mining sites that helps teams **see what changed on the ground**—using satellite imagery—without waiting for field reports.

It is designed for people who need clear answers quickly:

- environmental and ESG teams
- mine operations and management
- compliance officers
- auditors and regulators (read-only use)

MineWatch focuses on one core outcome: **detect, visualize, and report meaningful change inside and around a mining lease**.

---

## The problem it solves
Mining operations are expected to monitor:

- land disturbance
- vegetation loss and rehabilitation
- changes near sensitive areas
- activity near or outside approved boundaries

In many organizations, this work happens through:

- manual GIS processing
- expensive consultant reports
- delayed reporting cycles

That creates risk:

- changes are discovered late
- reporting takes too long
- audits become stressful and costly

---

## How MineWatch works (high level)
MineWatch follows a simple, repeatable workflow:

### 1) Define the “area of truth”
A user provides the mining lease boundary (a polygon) and a buffer zone around it.

This defines where monitoring matters.

### 2) Bring in satellite observations
MineWatch automatically finds recent satellite imagery over that area.

It uses trusted, widely accepted sources (such as Sentinel‑2), and records key metadata like:

- acquisition date
- cloud cover
- coverage footprint

### 3) Compare imagery over time
MineWatch compares a baseline image to a newer image to identify meaningful change.

For the MVP, the focus is intentionally practical:

- vegetation loss
- vegetation gain (rehabilitation)
- “no meaningful change”

### 4) Show results on a map
Users can view:

- the lease boundary
- the surrounding buffer zone
- highlighted change areas (“hotspots”)

This is the fastest way for a non-specialist to understand what happened.

### 5) Trigger alerts and generate reports
MineWatch can trigger simple alerts (no machine-learning required), such as:

- “vegetation loss exceeds X hectares”
- “change detected outside boundary”

It can also generate a compliance-friendly PDF report that summarizes:

- dates compared
- areas impacted
- key findings and alerts

---

## Where MineWatch is useful
MineWatch can support multiple real-world needs:

- **Compliance monitoring:** demonstrate adherence to boundaries and conditions
- **ESG reporting:** provide evidence of impact and rehabilitation progress
- **Operational oversight:** detect unexpected expansion or disturbance
- **Audit readiness:** keep repeatable, time-stamped records of monitoring outputs
- **Stakeholder communication:** share understandable map-based summaries

---

## What MineWatch is not (by design)
MineWatch is intentionally focused and avoids hype.

It does not try to be:

- a real-time surveillance system
- a fully automated “AI mining expert”
- a replacement for all environmental software

The goal is reliability and repeatability first.

---

## The long-term vision
Once the core workflow is solid, MineWatch can grow into:

- multi-site portfolio monitoring
- regulator portals and shareable read-only links
- more indices and change types (soil exposure, water changes)
- advanced monitoring options (e.g., subsidence)

But the foundation remains the same: **clear, defensible monitoring with minimal friction**.
