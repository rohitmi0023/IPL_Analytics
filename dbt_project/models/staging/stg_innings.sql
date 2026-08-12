select
    match_id,
    i.index + 1 as innings_no,
    i.value:team::VARCHAR(256) as batting_team,
    i.value:powerplays as powerplays
from {{ source('raw', 'raw_match_json') }} r,
    lateral flatten(input => r.raw_variant:innings) i
