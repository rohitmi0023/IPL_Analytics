select
    r.match_id,
    md5(p.value::varchar)::varchar(32) as player_id,
    p.value::varchar as player_name,
    t.key::varchar as team_name
from {{ source('raw', 'raw_match_json') }} r,
    lateral flatten(input => r.raw_variant:info:players) t,
    lateral flatten(input => t.value) p
