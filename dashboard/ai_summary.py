import json

import streamlit as st

from db import get_backend

CORTEX_MODEL = "llama3.1-70b"


@st.cache_data(show_spinner=False, ttl=3600)
def _probe_cortex() -> bool:
    try:
        row = get_backend().query_one(
            "select SNOWFLAKE.CORTEX.COMPLETE(?, ?)",
            [CORTEX_MODEL, "Reply with exactly: OK"],
        )
        return row is not None and "OK" in str(row[0]).upper()
    except Exception:
        return False


@st.cache_data(show_spinner=False, ttl=3600)
def build_facts() -> dict:
    b = get_backend()
    return {
        "summary": b.query("select * from V_MATCH_SUMMARY order by innings_no").to_dict("records"),
        "batting": b.query("select * from V_BATTING order by runs desc limit 10").to_dict("records"),
        "bowling": b.query(
            "select * from V_BOWLING order by wickets desc, economy limit 10"
        ).to_dict("records"),
        "phases": b.query("select * from V_PHASE order by innings_no").to_dict("records"),
        "partnerships": b.query("select * from V_PARTNERSHIP order by runs desc limit 5").to_dict("records"),
    }


def _cortex_commentary(facts: dict, backend) -> str:
    prompt = (
        "You are a cricket analyst. Using ONLY the facts provided below (JSON), write a concise "
        "3-4 sentence commentary on this IPL match. Do not invent facts, players, or numbers. "
        "Mention the result, the best individual batting and bowling performances, and one key "
        "phase or partnership.\n\nFACTS:\n"
        + json.dumps(facts, indent=2, default=str)
    )
    row = backend.query_one(
        "select SNOWFLAKE.CORTEX.COMPLETE(?, ?)",
        [CORTEX_MODEL, prompt],
    )
    return str(row[0]).strip()


def _template_commentary(facts: dict) -> str:
    s = facts["summary"]
    inn1 = next((r for r in s if r["INNINGS_NO"] == 1), {})
    inn2 = next((r for r in s if r["INNINGS_NO"] == 2), {})
    winner = inn2.get("WINNER") or inn1.get("WINNER")
    lines = []
    if winner:
        if inn2.get("RESULT_WICKETS") is not None:
            margin = f" by {inn2['RESULT_WICKETS']} wickets"
        elif inn2.get("RESULT_RUNS") is not None:
            margin = f" by {inn2['RESULT_RUNS']} runs"
        else:
            margin = ""
        lines.append(
            f"{winner} won{margin}. {inn1.get('BATTING_TEAM')} posted "
            f"{inn1.get('RUNS')}/{inn1.get('WICKETS')} in {inn1.get('OVERS')} overs "
            f"(run rate {inn1.get('RUN_RATE')}); {inn2.get('BATTING_TEAM')} replied with "
            f"{inn2.get('RUNS')}/{inn2.get('WICKETS')} in {inn2.get('OVERS')} overs."
        )
    if facts["batting"]:
        b = facts["batting"][0]
        lines.append(
            f"Top scorer was {b.get('BATTER')} with {b.get('RUNS')} runs off "
            f"{b.get('BALLS_FACED')} balls (strike rate {b.get('STRIKE_RATE')})."
        )
    if facts["bowling"]:
        b = facts["bowling"][0]
        lines.append(
            f"{b.get('BOWLER')} was the pick of the bowlers with {b.get('WICKETS')} "
            f"wicket(s) for {b.get('RUNS_CONCEDED')} runs (economy {b.get('ECONOMY')})."
        )
    if facts["partnerships"]:
        p = facts["partnerships"][0]
        lines.append(
            f"The largest partnership was {p.get('BATTER1')} and {p.get('BATTER2')}, "
            f"who added {p.get('RUNS')} runs."
        )
    return " ".join(lines)


@st.cache_data(show_spinner=False, ttl=3600)
def generate_commentary(use_cortex: bool, facts_key: str) -> dict:
    facts = json.loads(facts_key)
    if use_cortex:
        try:
            return {"engine": "Cortex LLM", "text": _cortex_commentary(facts, get_backend())}
        except Exception:
            pass
    return {"engine": "Template (Cortex unavailable)", "text": _template_commentary(facts)}


def commentary_available() -> tuple[bool, str]:
    use_cortex = _probe_cortex()
    status = "Cortex LLM available" if use_cortex else "Cortex unavailable on this account - using template"
    return use_cortex, status
