-- v_match_summary: one row per innings — team scorecard (runs, wickets, overs, run rate, extras, result).
with innings_agg as (
    select
        match_id,
        innings_no,
        batting_team,
        bowling_team,
        sum(runs_total)                        as runs,
        count_if(is_wicket)                    as wickets,
        count_if(legal_delivery)               as balls,
        sum(runs_extras)                       as extras
    from {{ ref('fact_ball') }}
    group by match_id, innings_no, batting_team, bowling_team
)
select
    m.match_id,
    m.season,
    m.city,
    m.venue,
    m.match_date,
    m.event_name,
    m.event_stage,
    i.innings_no,
    i.batting_team,
    i.bowling_team,
    i.runs,
    i.wickets,
    round(i.balls / 6.0, 1) as overs,
    round(i.runs * 6.0 / nullif(i.balls, 0), 2) as run_rate,
    i.extras,
    m.toss_winner,
    m.toss_decision,
    m.winner,
    m.result_runs,
    m.result_wickets,
    m.player_of_match
from innings_agg i
join {{ ref('dim_match') }} m on i.match_id = m.match_id
order by i.match_id, i.innings_no
