# Business Requirements Document (BRD)

## IPL Analytics — Ball-by-Ball Match Analysis

| | |
|---|---|
| **Document ID** | BRD-IPL-2026-001 |
| **Version** | v1 |
| **Status** | Draft |
| **Date** | 2026-08-06 |

---

## 1. Overview

Analysts currently analyze IPL match data through manual, ad-hoc processes — there is no single source of truth for ball-by-ball match information. This project builds a repeatable pipeline that ingests Cricsheet match JSON files into a queryable store, computes standard cricket analytics, and surfaces results through an interactive dashboard.

A Proof of Concept (POC) validates the pipeline end-to-end using a single match file (`981017.json` — IPL 2016 Qualifier 2: Gujarat Lions vs Sunrisers Hyderabad), then scales to additional matches and seasons.

---

## 2. Objectives

1. Centralize ball-by-ball match data in a single queryable repository.
2. Enable analysis at match, team, player, and ball granularity.
3. Compute standard cricket statistics automatically (batting, bowling, phases, partnerships).
4. Provide a self-serve interactive dashboard for analysts and stakeholders.
5. Establish a repeatable, scalable pipeline that can process hundreds of match files.

---

## 3. Scope

### In Scope

- Ingestion and validation of Cricsheet-format IPL match JSON files (POC: `981017.json`).
- Modeling of match-level and ball-level data for analysis.
- Computation of batting, bowling, phase, and partnership statistics.
- Interactive dashboard on the analytics (Gold) layer.
- Batch processing; scalable to full-season ingestion.

### Out of Scope

- Real-time / streaming ingestion.
- Weather, pitch, and venue analytics beyond source data.
- Player auction, salary, and off-field metadata.
- Web UI for manual data entry or correction.
- Production deployment and 24/7 support (POC phase).

---

## 4. Functional Requirements

| ID | Requirement |
|-----|-----|
| **FR-1** | **Ingest & validate** — System shall load IPL match JSON files, verify each is valid JSON with the required fields (`meta`, `info`, `innings`), and log/report any files that fail validation. |
| **FR-2** | **Model data for analysis** — System shall provide match-level data (teams, venue, toss, outcome/margin, player of match) and ball-level data (innings, over, batter, bowler, non-striker, runs, extras, wickets). |
| **FR-3** | **Compute match & player statistics** — System shall derive batting (runs, strike rate, boundaries), bowling (overs, runs conceded, wickets, economy), phase (powerplay/middle/death), and partnership statistics. |
| **FR-4** | **Interactive dashboard** — System shall provide a self-serve dashboard over the analytics layer covering match summaries, batting, bowling, phases, and partnerships. |

---

## 5. Non-Functional Requirements

| ID | Requirement |
|---|---|
| **NFR-1** | Pipeline shall process a full IPL season (~60 matches) in a single run without manual intervention. |
| **NFR-2** | Dashboard queries shall return results in < 10 seconds. |
| **NFR-3** | Loads shall be idempotent — re-running must not duplicate data or corrupt existing records. |
| **NFR-4** | Code shall be modular, documented, and version-controlled. |

---

## 6. Data Source

| Attribute | Detail |
|---|---|
| **Format** | JSON (Cricsheet specification, data version `1.0.0`) |
| **Granularity** | One file per match |
| **Sample** | `981017.json` — 2016 IPL Qualifier 2, Gujarat Lions vs Sunrisers Hyderabad, Delhi |
| **Size** | ~55 KB, 2 innings, 20 overs each |
| **Source** | Cricsheet (open dataset) |

---

## 7. Tech Stack

- **Language:** Python
- **Warehouse:** Snowflake
- **Transformation:** dbt Core
- **Dashboard:** Streamlit

---

## 8. Sample Analytical Questions

The platform must answer these after ingestion:

| # | Question |
|---|---|
| A1 | What was the final score, result, and margin for the match? |
| A2 | Which batter scored the most runs, and at what strike rate? |
| A3 | Which bowler had the best economy rate, and how many wickets? |
| A4 | How many boundaries (4s/6s) did each team hit? |
| A5 | What was the run rate in the powerplay vs. death overs? |
| A6 | What was the top partnership, and between which batters? |
| A7 | Why was the Player of the Match awarded (key contributions)? |

---

## 9. Glossary

| Term | Definition |
|---|---|
| **Innings** | One team's batting turn in a match (each team bats once in T20). |
| **Over** | Six legal deliveries bowled by one bowler. |
| **Powerplay** | Mandatory fielding restriction period — typically the first 6 overs in T20. |
| **Death overs** | Final overs of an innings (typically 16–20) where teams accelerate scoring. |
| **Extras** | Runs not scored off the bat: wides, no-balls, byes, leg-byes. |
| **Strike rate** | Runs scored per 100 balls faced. |
| **Economy rate** | Runs conceded per over bowled. |
| **Maiden over** | An over in which the bowler concedes zero runs. |
| **Partnership** | Runs scored while two specific batters are together at the crease. |

---

## 10. Future Enhancements

- Multi-season bulk ingestion with incremental loads.
- Historical / career player statistics and head-to-head analysis.
- Prediction / win-probability models on ball-level data.
- Scheduled pipeline runs and alerting.

---

*End of Document*
