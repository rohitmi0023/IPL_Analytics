-- v_bowling: one row per bowler per innings — bowling scorecard (overs, runs, wickets, economy, maidens).
with overs_agg as (
    select
        match_id,
        season,
        match_date,
        innings_no,
        bowler,
        over_no,
        sum(runs_total)                  as runs,
        count_if(legal_delivery)         as legal_balls
    from {{ ref('fact_ball') }}
    group by match_id, season, match_date, innings_no, bowler, over_no
),
maiden_overs as (
    select
        match_id,
        season,
        match_date,
        innings_no,
        bowler,
        count(*) as maidens
    from overs_agg
    where legal_balls = 6 and runs = 0
    group by match_id, season, match_date, innings_no, bowler
)
select
    fb.match_id,
    fb.season,
    fb.match_date,
    fb.innings_no,
    fb.bowling_team,
    fb.bowler,
    fb.bowler_id,
    count_if(fb.legal_delivery)  as balls_bowled,
    round(count_if(fb.legal_delivery) / 6.0, 1) as overs,
    sum(fb.runs_total)           as runs_conceded,
    count_if(fb.is_wicket and fb.wicket_kind <> 'run out') as wickets,
    round(sum(fb.runs_total) * 6.0 / nullif(count_if(fb.legal_delivery), 0), 2) as economy,
    count_if(fb.legal_delivery and fb.runs_total = 0) as dot_balls,
    sum(fb.runs_extras)          as extras_conceded,
    coalesce(mo.maidens, 0)      as maidens
from {{ ref('fact_ball') }} fb
left join maiden_overs mo
    on fb.match_id = mo.match_id
   and fb.innings_no = mo.innings_no
   and fb.bowler = mo.bowler
group by fb.match_id, fb.season, fb.match_date, fb.innings_no, fb.bowling_team, fb.bowler, fb.bowler_id, mo.maidens
order by fb.match_id, fb.innings_no, runs_conceded
