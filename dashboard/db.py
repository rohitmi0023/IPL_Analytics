import os

import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
USER = os.getenv("SNOWFLAKE_USER")
PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
ROLE = os.getenv("SNOWFLAKE_ROLE", "IPL_ENGINEER_ROLE")
WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "IPL_QUERY_WH")
DATABASE = os.getenv("SNOWFLAKE_DATABASE", "IPL_ANALYTICS_DB")
SCHEMA = "GOLD"


class Backend:
    def query(self, sql, params=None):
        raise NotImplementedError

    def query_one(self, sql, params=None):
        raise NotImplementedError


class SnowflakeConnectorBackend(Backend):
    def __init__(self):
        import snowflake.connector

        self.conn = snowflake.connector.connect(
            account=ACCOUNT,
            user=USER,
            password=PASSWORD,
            role=ROLE,
            warehouse=WAREHOUSE,
            database=DATABASE,
            schema=SCHEMA,
            paramstyle="qmark",
        )

    def query(self, sql, params=None):
        cur = self.conn.cursor()
        cur.execute(sql, params) if params else cur.execute(sql)
        return cur.fetch_pandas_all()

    def query_one(self, sql, params=None):
        cur = self.conn.cursor()
        cur.execute(sql, params) if params else cur.execute(sql)
        return cur.fetchone()


class SnowparkSessionBackend(Backend):
    def __init__(self):
        from snowflake.snowpark.context import get_active_session

        self.session = get_active_session()

    def query(self, sql, params=None):
        return self.session.sql(sql, params=params).to_pandas()

    def query_one(self, sql, params=None):
        rows = self.session.sql(sql, params=params).limit(1).collect()
        return tuple(rows[0]) if rows else None


@st.cache_resource(show_spinner=False)
def get_backend():
    try:
        from snowflake.snowpark.context import get_active_session

        get_active_session()
        return SnowparkSessionBackend()
    except Exception:
        return SnowflakeConnectorBackend()
