with player_names as (
    select
        distinct
        r.match_id,
        pp.value::varchar as player_name
    from {{ source('raw', 'raw_match_json') }} r,
    lateral flatten(input => r.raw_variant:info:players) p,
    lateral flatten(input => p.value) pp
)

select 
player_name,
cricsheet_id as player_id,
min(season) as first_season,
max(season) as last_season
from {{ ref('stg_registry') }} r
join {{ref('stg_matches')}} m
on r.match_id = m.match_id
join player_names p
on p.player_name = r.person_name
and p.match_id = r.match_id
group by 1, 2