with deliveries as (
    select
        d.match_id,
        d.innings_no,
        d.batting_team,
        case when d.batting_team = m.team_1 then m.team_2 else m.team_1 end as bowling_team,
        d.over_no,
        d.ball_in_over,
        d.batter,
        d.non_striker,
        d.bowler,
        d.runs_batter,
        d.runs_extras,
        d.runs_total,
        d.extras,
        d.wickets
    from {{ ref('stg_deliveries') }} d
    join {{ ref('stg_matches') }} m on d.match_id = m.match_id
)
select
    d.match_id,
    d.innings_no,
    d.batting_team,
    d.bowling_team,
    d.over_no,
    d.ball_in_over,
    d.batter,
    d.non_striker,
    d.bowler,
    tb.team_id   as batting_team_id,
    tw.team_id   as bowling_team_id,
    pb.player_id as batter_id,
    pns.player_id as non_striker_id,
    pw.player_id as bowler_id,
    d.runs_batter,
    d.runs_extras,
    d.runs_total,
    coalesce(d.extras:wides::int, 0) > 0   as is_wide,
    coalesce(d.extras:noballs::int, 0) > 0 as is_noball,
    coalesce(d.extras:byes::int, 0) > 0    as is_bye,
    coalesce(d.extras:legbyes::int, 0) > 0 as is_legbye,
    not (coalesce(d.extras:wides::int, 0) > 0 or coalesce(d.extras:noballs::int, 0) > 0) as legal_delivery,
    not (coalesce(d.extras:wides::int, 0) > 0) as batter_faced,
    coalesce(array_size(d.wickets), 0) > 0 as is_wicket,
    d.wickets[0]:kind::varchar       as wicket_kind,
    d.wickets[0]:player_out::varchar as player_out,
    d.wickets[0]:fielders[0]:name::varchar as fielder_name
from deliveries d
join {{ ref('dim_team') }}  tb on d.batting_team = tb.team_name
join {{ ref('dim_team') }}  tw on d.bowling_team = tw.team_name
join {{ ref('dim_player') }} pb  on d.match_id = pb.match_id  and d.batter = pb.player_name
join {{ ref('dim_player') }} pns on d.match_id = pns.match_id and d.non_striker = pns.player_name
join {{ ref('dim_player') }} pw  on d.match_id = pw.match_id  and d.bowler = pw.player_name
