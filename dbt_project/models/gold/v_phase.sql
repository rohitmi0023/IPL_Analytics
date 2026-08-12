-- v_phase: batting summary by phase (Powerplay / Middle / Death) per innings.
with balls as (
    select
        match_id,
        innings_no,
        batting_team,
        case
            when over_no <= 6 then 'Powerplay'
            when over_no <= 15 then 'Middle'
            else 'Death'
        end as phase,
        runs_total,
        legal_delivery,
        batter_faced,
        is_wicket
    from {{ ref('fact_ball') }}
)
select
    match_id,
    innings_no,
    batting_team,
    phase,
    count_if(batter_faced)  as balls_faced,
    sum(runs_total)         as runs,
    count_if(is_wicket)     as wickets,
    round(sum(runs_total) * 6.0 / nullif(count_if(batter_faced), 0), 2) as run_rate
from balls
group by match_id, innings_no, batting_team, phase
order by match_id, innings_no, phase
