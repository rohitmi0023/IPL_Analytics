with players_team as (
select 
r.match_id,
pt.key::varchar as team_name,
p.value::varchar as player_name
from {{ source('raw', 'raw_match_json') }} r,
lateral flatten (input => r.raw_variant:info:players) pt,
lateral flatten (input => pt.value) p
)
select 
sr.CRICSHEET_ID as player_id,
pt.match_id,
pt.team_name
from players_team pt
join {{ ref('stg_registry') }} sr
on sr.person_name = pt.player_name
and sr.match_id = pt.match_id