import json

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_summary import build_facts, commentary_available, generate_commentary
from db import get_backend

MARTS = "IPL_ANALYTICS_DB.MARTS"

TEAM_COLORS = {
    "Gujarat Lions": "#1f77b4",
    "Sunrisers Hyderabad": "#ff7f0e",
}

st.set_page_config(page_title="IPL Analytics", layout="wide")


def team_color(team):
    return TEAM_COLORS.get(team, "#636efa")


@st.cache_data(ttl=3600)
def load_matches():
    return get_backend().query(f"select match_id, season, match_date, team_1, team_2, venue from {MARTS}.DIM_MATCH order by match_date")


@st.cache_data(ttl=3600)
def load_gold(match_id):
    b = get_backend()
    return {
        "summary": b.query(
            "select * from V_MATCH_SUMMARY where match_id = ? order by innings_no", [match_id]
        ),
        "batting": b.query("select * from V_BATTING where match_id = ?", [match_id]),
        "bowling": b.query("select * from V_BOWLING where match_id = ?", [match_id]),
        "phases": b.query("select * from V_PHASE where match_id = ?", [match_id]),
        "partnerships": b.query("select * from V_PARTNERSHIP where match_id = ?", [match_id]),
    }


@st.cache_data(ttl=3600)
def load_overs(match_id):
    return get_backend().query(
        f"select innings_no, over_no, sum(runs_total) as runs, count_if(is_wicket) as wickets "
        f"from {MARTS}.FACT_BALL where match_id = ? group by 1, 2 order by 1, 2",
        [match_id],
    )


matches = load_matches()
seasons = sorted(matches["SEASON"].unique().tolist(), reverse=True)
selected_season = st.sidebar.selectbox("Season", ["All"] + [str(s) for s in seasons])

if selected_season != "All":
    filtered_matches = matches[matches["SEASON"] == int(selected_season)]
else:
    filtered_matches = matches

options = [f"{r.TEAM_1} vs {r.TEAM_2} ({r.MATCH_DATE})" for r in filtered_matches.itertuples()]
selected = st.sidebar.selectbox("Match", options)
match_id = int(filtered_matches.iloc[options.index(selected)].MATCH_ID)

gold = load_gold(match_id)
summary = gold["summary"]
batting = gold["batting"]
bowling = gold["bowling"]
phases = gold["phases"]
partnerships = gold["partnerships"]

team_choice = st.sidebar.selectbox("Team", ["All"] + sorted(summary["BATTING_TEAM"].unique().tolist()))

st.title("IPL Match Analytics")
st.caption(f"Match {match_id} · {selected}")

tab_summary, tab_batting, tab_bowling, tab_phases, tab_partners, tab_career, tab_ai = st.tabs(
    ["Match Summary", "Batting", "Bowling", "Phases", "Partnerships", "Player Career", "AI Commentary"]
)

with tab_summary:
    inn1 = summary[summary["INNINGS_NO"] == 1].iloc[0] if len(summary) > 0 else None
    inn2 = summary[summary["INNINGS_NO"] == 2].iloc[0] if len(summary) > 1 else None

    if inn2 is not None:
        if pd.notna(inn2["RESULT_WICKETS"]):
            margin = f" by {int(inn2['RESULT_WICKETS'])} wickets"
        elif pd.notna(inn2["RESULT_RUNS"]):
            margin = f" by {int(inn2['RESULT_RUNS'])} runs"
        else:
            margin = ""
        st.markdown(
            f"### {inn2['WINNER']} won{margin}  \n"
            f"Toss: {inn1['TOSS_WINNER']} chose to {str(inn1['TOSS_DECISION']).lower()}  ·  "
            f"Player of the match: **{inn1['PLAYER_OF_MATCH']}**  ·  Venue: {inn1['VENUE']}, {inn1['CITY']}"
        )

    for idx, row in summary.iterrows():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            f"{row['BATTING_TEAM']} (innings {int(row['INNINGS_NO'])})",
            f"{row['RUNS']}/{row['WICKETS']}",
        )
        col2.metric("Overs", row["OVERS"])
        col3.metric("Run rate", row["RUN_RATE"])
        col4.metric("Extras", row["EXTRAS"])

    st.subheader("Runs per over")
    over_df = load_overs(match_id)
    if len(over_df) > 0:
        label_map = {}
        for idx, row in summary.iterrows():
            label_map[int(row["INNINGS_NO"])] = f"Innings {int(row['INNINGS_NO'])} · {row['BATTING_TEAM']}"
        over_df["Innings"] = over_df["INNINGS_NO"].map(label_map)
        fig = px.line(
            over_df,
            x="OVER_NO",
            y="RUNS",
            color="Innings",
            markers=True,
            color_discrete_map={label_map[i]: team_color(summary.iloc[i - 1]["BATTING_TEAM"]) for i in label_map},
        )
        fig.update_layout(xaxis_title="Over", yaxis_title="Runs")
        st.plotly_chart(fig, width="stretch")

with tab_batting:
    view = batting if team_choice == "All" else batting[batting["BATTING_TEAM"] == team_choice]
    view = view.sort_values("RUNS", ascending=False)
    display = view[
        ["BATTER", "BALLS_FACED", "RUNS", "FOURS", "SIXES", "STRIKE_RATE", "DISMISSAL_KIND", "NOT_OUT"]
    ].copy()
    display["NOT_OUT"] = display["NOT_OUT"].map({True: "Yes", False: "No"})
    display.columns = ["Batter", "Balls", "Runs", "4s", "6s", "SR", "Dismissal", "Not out"]
    st.dataframe(display, hide_index=True, width="stretch")

    st.subheader("Top scorers")
    top = view.nlargest(8, "RUNS")
    if len(top) > 0:
        fig = px.bar(
            top,
            x="RUNS",
            y="BATTER",
            orientation="h",
            color="BATTING_TEAM",
            color_discrete_map=TEAM_COLORS,
        )
        fig.update_layout(xaxis_title="Runs", yaxis_title="")
        st.plotly_chart(fig, width="stretch")

with tab_bowling:
    view = bowling if team_choice == "All" else bowling[bowling["BOWLING_TEAM"] == team_choice]
    view = view.sort_values(["WICKETS", "ECONOMY"], ascending=[False, True])
    display = view[
        ["BOWLER", "OVERS", "RUNS_CONCEDED", "WICKETS", "ECONOMY", "DOT_BALLS", "MAIDENS"]
    ].copy()
    display.columns = ["Bowler", "Overs", "Runs", "Wkts", "Econ", "Dots", "Mdns"]
    st.dataframe(display, hide_index=True, width="stretch")

    st.subheader("Wickets vs runs conceded")
    if len(view) > 0:
        fig = px.scatter(
            view,
            x="RUNS_CONCEDED",
            y="WICKETS",
            size="BALLS_BOWLED",
            color="BOWLING_TEAM",
            hover_name="BOWLER",
            color_discrete_map=TEAM_COLORS,
        )
        fig.update_layout(xaxis_title="Runs conceded", yaxis_title="Wickets")
        st.plotly_chart(fig, width="stretch")

with tab_phases:
    view = phases if team_choice == "All" else phases[phases["BATTING_TEAM"] == team_choice]
    phase_order = ["Powerplay", "Middle", "Death"]
    view = view.sort_values("PHASE", key=lambda s: s.map({p: i for i, p in enumerate(phase_order)}))
    display = view[["BATTING_TEAM", "PHASE", "RUNS", "BALLS_FACED", "WICKETS", "RUN_RATE"]].copy()
    display.columns = ["Team", "Phase", "Runs", "Balls", "Wkts", "Run rate"]
    st.dataframe(display, hide_index=True, width="stretch")

    if len(view) > 0:
        fig = px.bar(
            view,
            x="PHASE",
            y="RUNS",
            color="BATTING_TEAM",
            barmode="group",
            category_orders={"PHASE": phase_order},
            color_discrete_map=TEAM_COLORS,
        )
        fig.update_layout(xaxis_title="", yaxis_title="Runs")
        st.plotly_chart(fig, width="stretch")

with tab_partners:
    view = partnerships if team_choice == "All" else partnerships[partnerships["BATTING_TEAM"] == team_choice]
    view = view.sort_values("RUNS", ascending=False)
    display = view[["WICKET_NUMBER", "BATTER1", "BATTER2", "RUNS", "BALLS_FACED", "RUN_RATE"]].copy()
    display.columns = ["Wicket #", "Batter 1", "Batter 2", "Runs", "Balls", "Run rate"]
    st.dataframe(display, hide_index=True, width="stretch")

    if len(view) > 0:
        view = view.copy()
        view["Pair"] = view["BATTER1"] + " + " + view["BATTER2"]
        fig = px.bar(
            view,
            x="RUNS",
            y="Pair",
            orientation="h",
            color="BATTING_TEAM",
            color_discrete_map=TEAM_COLORS,
        )
        fig.update_layout(xaxis_title="Runs", yaxis_title="")
        st.plotly_chart(fig, width="stretch")

with tab_career:
    st.subheader("Player Career Analytics")

    # Load all batting and bowling data for career aggregation
    @st.cache_data(ttl=3600)
    def load_all_batting():
        return get_backend().query(f"select * from V_BATTING")

    @st.cache_data(ttl=3600)
    def load_all_bowling():
        return get_backend().query(f"select * from V_BOWLING")

    all_batting = load_all_batting()
    all_bowling = load_all_bowling()

    all_players = sorted(set(all_batting["BATTER"].unique().tolist() + all_bowling["BOWLER"].unique().tolist()))
    selected_player = st.sidebar.selectbox("Player", all_players, key="player_select")

    # Filter to selected player
    player_bat = all_batting[all_batting["BATTER"] == selected_player]
    player_bowl = all_bowling[all_bowling["BOWLER"] == selected_player]

    # Batting career stats
    if len(player_bat) > 0:
        st.markdown(f"### Batting — {selected_player}")
        bat_stats = {
            "matches": player_bat["MATCH_ID"].nunique(),
            "total_runs": player_bat["RUNS"].sum(),
            "avg": round(player_bat["RUNS"].mean(), 1),
            "strike_rate": round(player_bat["STRIKE_RATE"].mean(), 1),
            "fours": int(player_bat["FOURS"].sum()),
            "sixes": int(player_bat["SIXES"].sum()),
        }

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Matches", bat_stats["matches"])
        c2.metric("Runs", bat_stats["total_runs"])
        c3.metric("Average", bat_stats["avg"])
        c4.metric("Strike Rate", bat_stats["strike_rate"])
        c5.metric("4s", bat_stats["fours"])
        c6.metric("6s", bat_stats["sixes"])

        # Season-by-season batting
        bat_season = player_bat.groupby("SEASON").agg(
            matches=("MATCH_ID", "nunique"),
            runs=("RUNS", "sum"),
            avg=("RUNS", "mean"),
            strike_rate=("STRIKE_RATE", "mean"),
        ).reset_index()
        bat_season["SEASON"] = bat_season["SEASON"].astype(int)

        fig = px.bar(
            bat_season, x="SEASON", y="runs", text="runs",
            labels={"SEASON": "Season", "runs": "Runs"},
        )
        fig.update_traces(textposition="outside")
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, width="stretch")

    # Bowling career stats
    if len(player_bowl) > 0:
        st.markdown(f"### Bowling — {selected_player}")
        bowl_stats = {
            "matches": player_bowl["MATCH_ID"].nunique(),
            "total_wickets": int(player_bowl["WICKETS"].sum()),
            "economy": round(player_bowl["ECONOMY"].mean(), 2),
            "total_runs": int(player_bowl["RUNS_CONCEDED"].sum()),
            "dot_balls": int(player_bowl["DOT_BALLS"].sum()),
        }

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Matches", bowl_stats["matches"])
        c2.metric("Wickets", bowl_stats["total_wickets"])
        c3.metric("Economy", bowl_stats["economy"])
        c4.metric("Runs Conceded", bowl_stats["total_runs"])
        c5.metric("Dot Balls", bowl_stats["dot_balls"])

        # Season-by-season bowling
        bowl_season = player_bowl.groupby("SEASON").agg(
            matches=("MATCH_ID", "nunique"),
            wickets=("WICKETS", "sum"),
            economy=("ECONOMY", "mean"),
        ).reset_index()
        bowl_season["SEASON"] = bowl_season["SEASON"].astype(int)

        fig = px.bar(
            bowl_season, x="SEASON", y="wickets", text="wickets",
            labels={"SEASON": "Season", "wickets": "Wickets"},
        )
        fig.update_traces(textposition="outside")
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, width="stretch")

    # Match-by-match detail
    if len(player_bat) > 0 or len(player_bowl) > 0:
        st.markdown("### Match-by-Match Detail")
        detail_frames = []
        if len(player_bat) > 0:
            bat_detail = player_bat[["SEASON", "MATCH_DATE", "BATTING_TEAM", "RUNS", "BALLS_FACED", "STRIKE_RATE", "FOURS", "SIXES", "DISMISSAL_KIND", "NOT_OUT"]].copy()
            bat_detail.columns = ["Season", "Date", "Team", "Runs", "Balls", "SR", "4s", "6s", "Dismissal", "Not Out"]
            bat_detail["Role"] = "Bat"
            detail_frames.append(bat_detail)
        if len(player_bowl) > 0:
            bowl_detail = player_bowl[["SEASON", "MATCH_DATE", "BOWLING_TEAM", "WICKETS", "OVERS", "RUNS_CONCEDED", "ECONOMY", "DOT_BALLS", "MAIDENS"]].copy()
            bowl_detail.columns = ["Season", "Date", "Team", "Wickets", "Overs", "Runs", "Econ", "Dots", "Maidens"]
            bowl_detail["Role"] = "Bowl"
            detail_frames.append(bowl_detail)
        if detail_frames:
            detail = pd.concat(detail_frames, ignore_index=True).sort_values("Date", ascending=False)
            st.dataframe(detail, hide_index=True, width="stretch")

with tab_ai:
    use_cortex, status = commentary_available()
    if use_cortex:
        st.success(status)
    else:
        st.info(status)
    st.write("Snowflake Cortex is used when available; otherwise a deterministic template generates the summary from the same gold-view facts.")
    st.caption("Prompt + facts are passed to SNOWFLAKE.CORTEX.COMPLETE; the response is grounded only in these numbers.")

    facts = {
        "summary": summary.to_dict("records"),
        "batting": batting.nlargest(10, "RUNS").to_dict("records"),
        "bowling": bowling.sort_values(["WICKETS", "ECONOMY"], ascending=[False, True])
        .head(10)
        .to_dict("records"),
        "phases": phases.to_dict("records"),
        "partnerships": partnerships.nlargest(5, "RUNS").to_dict("records"),
    }
    facts_key = json.dumps(facts, default=str)

    if st.button("Generate match commentary", type="primary"):
        with st.spinner("Generating..."):
            result = generate_commentary(use_cortex, facts_key)
        st.markdown(f"**Engine:** {result['engine']}")
        st.markdown(result["text"])
