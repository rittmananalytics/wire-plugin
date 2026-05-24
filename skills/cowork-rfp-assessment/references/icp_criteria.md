# Rittman Analytics — Ideal Customer Profile Scoring Criteria

Version 1.0 — update after each closed quarter.

---

## Scoring rubric

Score each dimension 0–10 based on evidence in the RFP or enquiry.

---

### 1. Tech stack fit (weight: 25%)

| Score | Criteria |
|-------|---------|
| 9–10 | dbt + Looker + BigQuery/Snowflake/Databricks. Established modern data stack. Active dbt Cloud users. |
| 7–8 | dbt present OR Looker present. One pillar of modern stack confirmed. Open to adding the other. |
| 5–6 | Moving from legacy stack to cloud. Greenfield migration where RA can shape the architecture. |
| 3–4 | Mixed signals — modern tools mentioned alongside legacy (Tableau, SSAS, on-prem Postgres). Partial modernisation. |
| 1–2 | Legacy stack dominant. Tableau/Power BI mandate implied but not explicit. Modernisation not yet on roadmap. |
| 0 | Explicit Tableau or Power BI mandate. On-premises only. No cloud deployment. |

---

### 2. Commercial fit (weight: 20%)

| Score | Criteria |
|-------|---------|
| 9–10 | Budget £100k+, fixed-price or T&M project, clear timeline, internal champion with budget authority. |
| 7–8 | Budget £50k–£100k or implied equivalent. Commercial terms flexible. Decision process clear. |
| 5–6 | Budget £25k–£50k. Scope well-defined but potentially tight. Good prospect for a scoped phase 1. |
| 3–4 | Budget unclear or below £25k. Staff aug framing. Multiple competing agencies. Long procurement cycle. |
| 1–2 | Strong indicators of budget constraint, IR35 risk, or commodity price competition. |
| 0 | Sub-£25k. IR35-inside requirement. Panel of 10+ with no criteria. |

---

### 3. Project type fit (weight: 20%)

| Score | Criteria |
|-------|---------|
| 9–10 | Core RA sweet spot: dbt model build, Looker dashboard delivery, data platform migration, data strategy advisory. |
| 7–8 | Adjacent to core: data quality implementation, semantic layer design, Dagster/dbt Cloud orchestration. |
| 5–6 | Adjacent but stretching: AI/ML use case framing, real-time ingestion, application build with analytics layer. |
| 3–4 | Outside core: pure data engineering (no analytics layer), front-end BI only (no modelling), pure cloud infra. |
| 1–2 | Staff augmentation, body-shopping, or permanent placement framing. |
| 0 | Pure staff aug. Permanent hire. No advisory or build component. |

---

### 4. Company / team profile (weight: 15%)

| Score | Criteria |
|-------|---------|
| 9–10 | 500–5,000 employees. Dedicated data team of 3–20. Head of Data or CDO as sponsor. Growth-stage or scale-up. |
| 7–8 | 200–500 employees or 5,000–20,000. Small data team (1–3) scaling up. Clear internal ownership. |
| 5–6 | 50–200 employees (early data function) or large enterprise (complex procurement). Sponsor identified. |
| 3–4 | Very early stage (<50 employees, no data team) or very large enterprise (50k+, slow procurement, committee decisions). |
| 1–2 | No internal data ownership. Sponsor unclear. Decision-making process opaque or committee-driven without a champion. |
| 0 | No named sponsor. Decision process completely unclear. |

---

### 5. Sector fit (weight: 10%)

| Score | Criteria |
|-------|---------|
| 9–10 | E-commerce, retail, fashion/apparel, marketplace, SaaS, fintech, financial services — RA has case studies and proven patterns. |
| 7–8 | Healthcare tech, edtech, travel/hospitality, media/publishing, logistics — adjacent sectors with transferable patterns. |
| 5–6 | Manufacturing, telecoms, energy/utilities — viable but require domain upskilling. |
| 3–4 | Highly regulated: banking (tier 1), insurance (Lloyds), pharma — slow procurement, compliance overhead. |
| 1–2 | Sectors with heavy vendor lock-in to tools RA doesn't support. |
| 0 | Public sector, government, NHS, local authority, defence. |

---

### 6. Geography (weight: 10%)

| Score | Criteria |
|-------|---------|
| 9–10 | UK-based, remote-friendly. London or major UK city. No mandatory on-site requirement. |
| 7–8 | EU-based, remote-first, or North American company with distributed team (compatible timezone). |
| 5–6 | APAC or Americas with significant timezone overlap requirement but remote acceptable. |
| 3–4 | Significant on-site requirement (>2 days/week) outside RA home base. |
| 1–2 | On-site mandate with relocation expectation, or geography incompatible with remote delivery. |
| 0 | On-premises infrastructure only. No remote access. |

---

## Hard disqualifiers (any one = automatic Decline)

1. **Tableau or Power BI mandate** — explicit requirement to deliver in Tableau or Power BI, and client will not consider Looker
2. **On-premises only** — no cloud deployment permitted; all infrastructure must remain on-prem
3. **Public sector** — government, NHS, local authority, or defence contractor
4. **Sub-£25k budget** — total engagement value below £25,000 (or equivalent)
5. **Staff augmentation only** — no advisory or build component; pure resource provision
6. **IR35-inside contracting** — requires permanent or inside-IR35 placement
7. **Commodity panel procurement** — competing with 10+ agencies with no articulated evaluation criteria

---

## Sector × tech stack quick reference

| Sector | Typical stack | RA fit |
|--------|--------------|-------|
| E-commerce / retail | Shopify + GA4 + BigQuery + dbt + Looker | ⭐⭐⭐⭐⭐ |
| SaaS / tech | Segment + BigQuery/Snowflake + dbt + Looker/Tableau | ⭐⭐⭐⭐⭐ |
| Fintech | Snowflake + dbt + Looker | ⭐⭐⭐⭐ |
| Healthcare tech | BigQuery + dbt (usually greenfield) | ⭐⭐⭐⭐ |
| Financial services | Oracle/SQL Server + BI tools — modernising | ⭐⭐⭐ |
| Manufacturing | SAP + on-prem SQL Server | ⭐⭐ |
| Public sector | Oracle + legacy BI | ❌ |

---

## Notes for updating this rubric

Review after each closed quarter. Key questions:
- Which won deals scored below 6? Why did we win them?
- Which lost deals scored above 7? Why did we lose?
- Are there new sectors or project types to add?
- Has the ICP weighting shifted based on where we're delivering best?
