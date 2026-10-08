-- Example snapshot: snapshots/snapshot_back_office/snapshot_back_office__users.sql
-- Records the state of back_office.users over time, because the source overwrites a user's row on
-- every change. The block name equals the file name. Source columns are held unchanged; renaming
-- happens in stg_back_office__users, which reads this snapshot the same way it reads a source.
-- Written to the snapshots schema by dbt_project.yml (new projects and new releases).

{% snapshot snapshot_back_office__users %}

{{
    config(
        unique_key = 'id',
        strategy = 'timestamp',
        updated_at = 'updated_at'
    )
}}

select * from {{ source('back_office', 'users') }}

{% endsnapshot %}

-- Where the source has no reliable modified timestamp, use the check strategy and list every
-- column whose change should create a new version:
--
--     strategy = 'check',
--     check_cols = ['name', 'email', 'country_code', 'active']
--
-- The dbt meta columns (dbt_valid_from, dbt_valid_to, dbt_scd_id, dbt_updated_at) keep their names.
-- id is not unique in the snapshot; dbt_scd_id is.
