-- v_batting: one row per batter per innings — batting scorecard (runs, balls, fours, sixes, strike rate, dismissal).
select
    match_id,
    innings_no,
    batting_team,
    batter,
    batter_id,
    count_if(batter_faced)                          as balls_faced,
    sum(runs_batter)                                as runs,
    count_if(batter_faced and runs_batter = 4)      as fours,
    count_if(batter_faced and runs_batter = 6)      as sixes,
    round(sum(runs_batter) * 100.0 / nullif(count_if(batter_faced), 0), 2) as strike_rate,
    max(case when is_wicket and player_out = batter then wicket_kind end)   as dismissal_kind,
    min(case when is_wicket and player_out = batter then 0 else 1 end) = 1  as not_out
from {{ ref('fact_ball') }}
group by match_id, innings_no, batting_team, batter, batter_id
order by match_id, innings_no, runs desc
