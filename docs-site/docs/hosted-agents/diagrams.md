---
title: Diagrams
sidebar_position: 8
---

# Hosted agents: diagrams

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

The three diagrams the other pages in this section use, together.

## Pod structure

```mermaid
flowchart TB
  P["Escalation contacts<br/>(people)"]
  EL["Engagement lead<br/>voice of the customer, rulings, QA and code review"]
  DM["Delivery manager<br/>plans, assigns, sprints, delivery reviews"]
  AE["Analytics engineers<br/>models, dbt, semantic layer, dashboards"]
  DE["Data engineers<br/>ingestion, pipelines, orchestration"]
  P --- EL
  EL --- DM
  EL --- AE
  EL --- DE
  DM -.->|day-to-day work| AE
  DM -.->|day-to-day work| DE
```

## How work flows: who does each step

```mermaid
flowchart TB
  subgraph PERSON["Person"]
    direction TB
    A1([Agree scope and SoW])
    A9{{Decision a person<br/>must take}}
    A10([Merge release to<br/>default branch])
  end
  subgraph EL["Engagement lead"]
    direction TB
    B1[Delivery request]
    B5{Ruling within<br/>governance?}
    B6[QA and code review]
    B7{Passes?}
    B8[Merge into<br/>release branch]
  end
  subgraph DM["Delivery manager"]
    direction TB
    C1[Set up release<br/>with Wire]
    C2[Plan tickets,<br/>import to release]
    C3[Sprint: all<br/>in-scope tickets]
    C4[Assign by<br/>role and load]
    C5[Delivery review<br/>twice a day]
  end
  subgraph ENG["Engineers"]
    direction TB
    D1[Ticket branch from<br/>release branch]
    D2[Propose plan]
    D3[Build and test]
    D4[Pull request into<br/>release branch]
  end
  A1 --> B1 --> C1 --> C2 --> C3 --> C4 --> D1 --> D2
  D2 -->|plan| B5
  B5 -->|yes| D3
  B5 -->|no| A9 --> D3
  D3 --> D4 --> B6 --> B7
  B7 -->|rework| D3
  B7 -->|pass| B8 --> C5
  C5 -->|next tickets| C4
  C5 -->|release done| A10
```

## Who takes a decision

```mermaid
flowchart TD
  Q[An agent needs a decision] --> K{Which kind of decision?<br/>see the governance template}
  K -->|always a person:<br/>scope, security and access, client data,<br/>production, code into the default branch| P[Person decides]
  K -->|release set-up or the delivery plan| DMd[Delivery manager decides]
  K -->|any other kind| T{Project's template}
  T -->|light| EL[Engagement lead decides]
  T -->|strict: routine and non-destructive,<br/>technical choices and QA checks| EL
  T -->|strict: everything else| P
  EL -.->|unsure, or the documents do not settle it| P
```
