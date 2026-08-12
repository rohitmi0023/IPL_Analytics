select
    md5(team_name)::varchar(32) as team_id,
    team_name
from (
    select team_1 as team_name from {{ ref('stg_matches') }}
    union
    select team_2 as team_name from {{ ref('stg_matches') }}
)
