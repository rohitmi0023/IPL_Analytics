import json

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
options = [f"{r.TEAM_1} vs {r.TEAM_2} ({r.MATCH_DATE})" for r in matches.itertuples()]
selected = st.sidebar.selectbox("Match", options)
match_id = int(matches.iloc[options.index(selected)].MATCH_ID)

gold = load_gold(match_id)
summary = gold["summary"]
batting = gold["batting"]
bowling = gold["bowling"]
phases = gold["phases"]
partnerships = gold["partnerships"]

team_choice = st.sidebar.selectbox("Team", ["All"] + sorted(summary["BATTING_TEAM"].unique().tolist()))

st.title("IPL Match Analytics")
st.caption(f"Match {match_id} · {selected}")

tab_summary, tab_batting, tab_bowling, tab_phases, tab_partners, tab_ai = st.tabs(
    ["Match Summary", "Batting", "Bowling", "Phases", "Partnerships", "AI Commentary"]
)

with tab_summary:
    inn1 = summary[summary["INNINGS_NO"] == 1].iloc[0] if len(summary) > 0 else None
    inn2 = summary[summary["INNINGS_NO"] == 2].iloc[0] if len(summary) > 1 else None

    if inn2 is not None:
        if inn2["RESULT_WICKETS"] is not None:
            margin = f" by {int(inn2['RESULT_WICKETS'])} wickets"
        elif inn2["RESULT_RUNS"] is not None:
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
