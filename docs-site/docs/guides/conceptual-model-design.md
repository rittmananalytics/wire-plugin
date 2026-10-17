---
sidebar_position: 1
title: Conceptual Data Model Design
description: How the conceptual model governs the data warehouse and semantic layer, how to tell an entity from its attributes, when to build an _xa table, and a checklist before building a warehouse model.
---

# Conceptual Data Model Design

This page defines best practices for conceptual data model for Wire. It provides a brief explanation of business ontology (how stakeholders understand, describe, and communicate about the business) and serves as the governing blueprint for our data warehouse and semantic layer design.

## Guidelines for Engineers

### Why We Govern with a Conceptual Ontology

Without clear governance, warehouse models tend to mirror the physical structure of source system tables rather than the shape of the business. Over time, this introduces semantic entropy: a single business concept gets fragmented across multiple tables, making it difficult for end users and AI agents to navigate the semantic layer or know which table holds the truth.

To prevent this sprawl, our conceptual model establishes a single, business-first ontology organised by domain. Every dbt model in the warehouse layer must map 1:1 to a single agreed entity in the conceptual model. We model business concepts, not raw source tables or system logs.

### Understanding Entities: Primary vs. Predicate Substance

An **entity** is a distinct business object or concept that an organisation tracks and analyses (for example, a `customer`, a `sale`, or a `supplier`). To decide whether something is a true entity or belongs inside an existing table, we distinguish between **primary substance** and **predicate substance**:

- **Primary substance (The Entity / Fixed Grain):** What one row of the table fundamentally *is*. A primary substance stands on its own with an independent business identity. In Aristotelian terms, it is *"not said-of and not present-in"* another thing.
- **Predicate substance (Attributes, Statuses, and Measures):** What is *said about* or *present in* that entity, such as its descriptive qualities, quantities, statuses, and lifecycle timestamps. Predicate substance cannot exist without the primary substance it describes; it belongs inside that entity's warehouse table (e.g., order date, order status, sales channel, and order total on `sales`).

**The core rule:** New attributes, measures, or workflow milestones describing an existing entity (such as its current status, approval date, or completion date) are **predicate substance** of that entity. They should be used to enrich the existing entity's model rather than split into separate supporting tables.

**When is something a separate entity?** A related concept only becomes its own entity when it has a genuinely different primary substance and grain, such as `sales` (one row per customer order) and `sales lines` (one row per item on an order). Even then, a new warehouse table may only be built **after** the entity has been agreed and added to this conceptual model.

A quick way to spot an ontological mistake (compound-name smell test) is to look at the proposed entity name. A two-word name is valid when the second word defines a true child grain of the first, such as `sales lines`, `shipment lines`, or `return lines`. However, if a table name stitches two existing business concepts together, or chains multiple qualifiers onto a noun, treat it as a red flag.

### Derived and Aggregated Tables (`_xa`) and Semantic Layer Aggregate Awareness

Our model includes **Derivations** (denoted by `_xa`, such as `sales xa`, or `churn xa`) alongside base dimensions (`_dim`) and facts (`_fact`). A Derivation does not introduce a new primary substance; it is a pre-computed aggregation or cross-domain summary of existing entities.

Because semantic layers can aggregate base facts and join dimensions dynamically at query time, **do not build pre-aggregated dbt models by default**. Only build a derived `_xa` table in the warehouse when:

1. It is explicitly governed in the model for complex cross-domain synthesis (such as `churn xa`), or
2. Pre-aggregation is required to optimise query performance and warehouse cost on high-volume tables.

When a pre-aggregated rollup table is built for performance, it must not be exposed as a competing table that forces users or AI agents to guess which view to query.

### Working with Coding Assistants

Left unguided, coding assistants will follow the structure of the raw source data, often proposing a separate `fact`, `dim`, or summary table for every source table, status log, or sub-process it encounters.

Always check any entity a coding assistant proposes against the design first. If the conceptual model does not cover your use case, or if an existing entity definition needs refining, agree with stakeholders and update this document *before* building in dbt.

### Checklist Before Building a Warehouse Model

1. **Name the primary substance:** State what one row represents in a single, plain-English business sentence using stakeholder terminology.
2. **Distinguish primary from predicate substance:** Does this data have its own independent grain (like `sales lines` vs. `sales`), or does it describe the details, status, or milestones of an existing entity? If it describes an existing entity, add it as columns (predicate substance) to that entity's model.
3. **Run the compound-name smell test:** Does your proposed model name combine two separate business concepts, bake a filter/type into the table name, or stack multiple nouns? If so, you are likely looking at a relationship or predicate substance of an existing entity.
4. **Avoid unagreed rollup tables:** Can this metric or summary be calculated dynamically in the semantic layer from existing base entities, or aggregate awareness?
5. **Check for domain overlap:** Is this concept already governed under another entity?
6. **Apply the semantic layer test:** If an end user or AI agent asks a question, will having this as a separate table make the semantic layer clearer, or will it force them to guess between overlapping tables?
7. **Govern first, build second:** If a genuinely new entity is needed (or an existing one needs renaming), update the design and agree it with stakeholders before creating the dbt model.

## References

- https://lewischarlesbaker.substack.com/p/the-real-and-the-hard-problem-of
- https://docs.getmodality.io/guide/conceptual-modeling.html
- https://blog.rittmananalytics.com/data-modelling-and-the-semantic-layer-39432f08d5ee
