{% docs user_pk %}
The surrogate primary key of the user entity, generated from the back-office
user account id. Stable across loads.
{% enddocs %}

{% docs account_fk %}
The surrogate key of the account the row belongs to. Joins to account_pk on
the account dimension.
{% enddocs %}

{% docs user_natural_key %}
The back-office identifier for the user account. Case-sensitive: kept as
received, never lowercased.
{% enddocs %}

{% docs user_account_natural_key %}
The back-office identifier of the billing account the user belongs to.
Case-sensitive: kept as received.
{% enddocs %}

{% docs user_name %}
The user's full name, lowercased.
{% enddocs %}

{% docs user_email %}
The user's email address, lowercased and trimmed.
{% enddocs %}

{% docs user_country_code %}
The user's ISO 3166-1 alpha-2 country code, lowercased. Null where the user
gave no country.
{% enddocs %}

{% docs user_account_balance_amount %}
The prepaid balance on the user's account, in the base currency (GBP), as a
decimal (19.99 is 19 pounds 99 pence).
{% enddocs %}

{% docs user_average_session_duration_seconds %}
The user's average session length over the last 30 days, in seconds.
{% enddocs %}

{% docs user_profile_completion_ratio %}
The share of profile fields the user has completed, from 0 to 1.
{% enddocs %}

{% docs user_is_active %}
True where the user can sign in. Accounts created before the flag existed
are active.
{% enddocs %}

{% docs user_was_deleted %}
True where the user account was deleted in the back office.
{% enddocs %}

{% docs user_created_dt %}
The date the user account was created. UTC.
{% enddocs %}

{% docs user_updated_ts %}
When the user account was last changed in the back office. UTC.
{% enddocs %}
