-- v_partnership: one row per batting partnership per innings (pair, runs, balls, strike rate).
with balls as (
    select
        match_id,
        innings_no,
        batting_team,
        over_no,
        ball_in_over,
        batter,
        non_striker,
        runs_total,
        batter_faced,
        is_wicket,
        row_number() over (partition by match_id, innings_no order by over_no, ball_in_over) as ball_seq
    from {{ ref('fact_ball') }}
),
flagged as (
    select *,
        coalesce(lag(is_wicket) over (partition by match_id, innings_no order by ball_seq), false) as prev_ball_wicket
    from balls
),
grouped as (
    select *,
        sum(case when prev_ball_wicket then 1 else 0 end)
            over (partition by match_id, innings_no order by ball_seq rows between unbounded preceding and current row) as partnership_id
    from flagged
),
first_ball as (
    select
        match_id,
        innings_no,
        batting_team,
        partnership_id,
        batter as batter1,
        non_striker as batter2,
        min(ball_seq) as first_seq
    from grouped
    group by match_id, innings_no, batting_team, partnership_id, batter, non_striker
    qualify row_number() over (partition by match_id, innings_no, partnership_id order by first_seq) = 1
)
select
    g.match_id,
    g.innings_no,
    g.batting_team,
    g.partnership_id + 1 as wicket_number,
    fb.batter1,
    fb.batter2,
    count_if(g.batter_faced) as balls_faced,
    sum(g.runs_total)        as runs,
    round(sum(g.runs_total) * 6.0 / nullif(count_if(g.batter_faced), 0), 2) as run_rate,
    count_if(g.is_wicket)    as wickets
from grouped g
join first_ball fb
    on g.match_id = fb.match_id
   and g.innings_no = fb.innings_no
   and g.batting_team = fb.batting_team
   and g.partnership_id = fb.partnership_id
group by g.match_id, g.innings_no, g.batting_team, g.partnership_id, fb.batter1, fb.batter2
order by g.match_id, g.innings_no, g.partnership_id
