select
r.match_id,
i.index+1 as innings_no,
i.value:team::VARCHAR(256) as batting_team,
o.index+1::INT as over_no,
d.index+1::INT as ball_in_over,
d.value:batter::VARCHAR as batter,
d.value:non_striker::VARCHAR as non_striker,
d.value:bowler::VARCHAR as bowler,
d.value:runs:batter::INT as runs_batter,
d.value:runs:extras::INT as runs_extras,
d.value:runs:total::INT as runs_total,
d.value:extras as extras,
d.value:wickets as wickets
from {{ source('raw', 'raw_match_json') }} r,
lateral flatten(input => r.raw_variant:innings) i,
lateral flatten(input => i.value:overs) o,
lateral flatten(input => o.value:deliveries, outer => true) d
