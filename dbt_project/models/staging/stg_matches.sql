select
    match_id,
    raw_variant:info:season::INT as season,
    raw_variant:info:city::VARCHAR as city,
    raw_variant:info:venue::VARCHAR as venue,
    raw_variant:info:dates[0]::DATE as match_date,
    raw_variant:info:event:name::VARCHAR as event_name,
    raw_variant:info:event:stage::VARCHAR as event_stage,
    raw_variant:info:teams[0]::VARCHAR as team_1,
    raw_variant:info:teams[1]::VARCHAR as team_2,
    raw_variant:info:toss:winner::VARCHAR as toss_winner,
    raw_variant:info:toss:decision::VARCHAR as toss_decision,
    raw_variant:info:outcome:winner::VARCHAR as winner,
    raw_variant:info:outcome:by:runs::INT as result_runs,
    raw_variant:info:outcome:by:wickets::INT as result_wickets,
    raw_variant:info:player_of_match[0]::VARCHAR as player_of_match,
    raw_variant:info:match_type::VARCHAR as match_type,
    raw_variant:info:gender::VARCHAR as gender
from {{ source('raw', 'raw_match_json') }}
