-- One row per person per match from the Cricsheet registry.
-- Includes players AND officials; dim_player filters to players only.

SELECT
r.match_id,
re.key::varchar as person_name,
re.value::varchar as cricsheet_id
FROM {{ source('raw', 'raw_match_json') }} r,
lateral flatten(input => r.RAW_VARIANT:info:registry:people) re
