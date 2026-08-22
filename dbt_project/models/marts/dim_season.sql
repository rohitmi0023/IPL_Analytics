with season_dates as (
    select
        season,
        count(*) as total_matches,
        min(MATCH_DATE) as start_date,
        max(MATCH_DATE) as end_date
    from {{ ref('dim_match') }}
    group by season
),
season_champion as (
    select
        season,
        winner as champion
    from {{ ref('dim_match') }}
    where event_stage = 'Final'
)
select
    sd.season,
    sd.total_matches,
    sd.start_date,
    sd.end_date,
    sc.champion
from season_dates sd
left join season_champion sc
on sc.season = sd.season
