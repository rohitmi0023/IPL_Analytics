{{
    config(
        materialized='incremental',
        unique_key='delivery_key',
        on_schema_change='append_new_columns'
    )
}}

with deliveries as (
    select
        d.match_id,
        m.season,
        m.match_date,
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
        d.wickets,
        d.loaded_at
    from {{ ref('stg_deliveries') }} d
    join {{ ref('stg_matches') }} m on d.match_id = m.match_id
)
select
    {{dbt_utils.generate_surrogate_key(['d.match_id', 'd.innings_no', 'd.over_no', 'd.ball_in_over'])}} as delivery_key,
    d.match_id,
    d.season,
    d.match_date,
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
    sr_b.cricsheet_id::varchar(32)  as batter_id,
    sr_ns.cricsheet_id::varchar(32) as non_striker_id,
    sr_bw.cricsheet_id::varchar(32) as bowler_id,
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
    d.wickets[0]:fielders[0]:name::varchar as fielder_name,
    d.loaded_at
from deliveries d
join {{ ref('dim_team') }} tb on d.batting_team = tb.team_name
join {{ ref('dim_team') }} tw on d.bowling_team = tw.team_name
join {{ ref('stg_registry') }} sr_b  on d.match_id = sr_b.match_id  and d.batter = sr_b.person_name
join {{ ref('stg_registry') }} sr_ns on d.match_id = sr_ns.match_id and d.non_striker = sr_ns.person_name
join {{ ref('stg_registry') }} sr_bw on d.match_id = sr_bw.match_id and d.bowler = sr_bw.person_name

{% if is_incremental() %}
where loaded_at > (select coalesce(max(loaded_at), '1970-01-01') from {{ this }})
{% endif %}
