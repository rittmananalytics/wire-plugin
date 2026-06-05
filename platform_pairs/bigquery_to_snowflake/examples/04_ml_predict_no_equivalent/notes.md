# Translation notes — `ML.PREDICT` has no direct Snowflake equivalent

This is the most disruptive single pattern in a BigQuery → Snowflake migration. It cannot be translated mechanically. The team must take an architectural decision, document it in `migration_strategy.md`, and then implement.

## What changed

| BigQuery | Snowflake | Path |
|---|---|---|
| `ML.PREDICT(MODEL \`project.model\`, ...)` | Snowflake Cortex ML | Path A — best fit if the model is logistic regression, gradient boosting, or another Cortex-supported family |
| `ML.PREDICT(MODEL \`project.model\`, ...)` | External function to Cloud Function / Lambda hosting the original model artifact | Path B — keeps the original model behaviour, adds network hop |
| `ML.PREDICT(MODEL \`project.model\`, ...)` | Remove from dbt, replace with batch scoring outside the warehouse | Path C — if the model is rarely scored, run it as a separate ML pipeline writing back to the warehouse |

The `after.sql` shown demonstrates **Path B** — the most common choice when the team wants behaviour-identical predictions and isn't ready to retrain on Cortex.

## Why no direct equivalent exists

BigQuery ML co-locates the model and the data — `ML.PREDICT` is just a SQL function over a model that BigQuery hosts. Snowflake doesn't host arbitrary user-trained models in the same way. Snowflake Cortex hosts a set of supported model families and Snowflake-trained models; arbitrary externally-trained models (especially TensorFlow / scikit-learn / XGBoost models exported by BigQuery ML) must run somewhere else and be called from SQL.

## Path A — Snowflake Cortex

Use when:
- The model is a supported Cortex family (linear regression, logistic regression, gradient boosting).
- The team accepts retraining on Snowflake-resident data (the model coefficients won't be identical).
- The model needs to evolve over time — Cortex retrain is part of the platform.

Migration work: retrain the model on Snowflake using `CORTEX.PREDICT` or the supervised learning APIs. The dbt model rewrites to `select cortex.predict(...) from ...`. Path A is the cleanest end state but requires retraining work that may or may not be in the migration's scope.

## Path B — External function

Use when:
- The team needs behaviour-identical predictions (regulatory / audit requirement).
- The model is complex (deep neural net, custom architecture) and retraining on Cortex isn't viable.
- An additional network hop per row is acceptable.

Migration work:
1. Export the BigQuery ML model artifact as TensorFlow SavedModel.
2. Wrap it in a Cloud Function (or Lambda) that accepts row-shaped JSON and returns prediction-shaped JSON.
3. Create a Snowflake external function pointing at that endpoint — typically via API Integration + Function.
4. Rewrite the dbt model as shown in `after.sql`.

The `target_setup` artifact must include the external function creation. This is not optional — the dbt model will not compile without it.

## Path C — Remove from dbt

Use when:
- The model is scored infrequently (weekly, monthly).
- Real-time SQL-time scoring isn't required.
- The team has an ML platform (Vertex AI, Databricks, SageMaker) that can run the model on a schedule and write predictions to a Snowflake table.

Migration work: remove `fct_churn_predictions.sql` from the dbt project. Add a scheduled batch job in the ML platform of choice. The downstream models that consumed `fct_churn_predictions` now read from a table populated by that batch job — same column names, same grain.

## dbt config impact

- **Path A**: model materialisation likely changes to `incremental` because Cortex inference cost matters.
- **Path B**: no config change; behaviour-identical to BQ except for the external function hop.
- **Path C**: model is removed; downstream models change their `ref()` to a source().

## Wire macro equivalent

There is no macro for this. Wire's `dbt_migration-generate` detects `ML.PREDICT` in the source models and flags them as `migration_approach: evaluate` rather than auto-translating. The migration_strategy artifact then captures the team's path choice per model.

## Validation

`dbt_migration-validate` checks that no Snowflake-target dbt model contains a literal `ml.predict` reference. If one slips through, validation fails — the model needs an explicit Path A/B/C decision before it can be approved.
