-- ============================================================
-- IPL Analytics — Streamlit in Snowflake Deploy
-- Creates the stage + Streamlit app in the GOLD schema.
-- IPL_ENGINEER_ROLE owns GOLD (via dbt), so it can create both objects.
-- Run fully as IPL_ENGINEER_ROLE. Safe to re-run (OR REPLACE).
-- After running, upload dashboard/app.py, db.py, ai_summary.py to
-- @IPL_ANALYTICS_DB.GOLD.IPL_STREAMLIT_STAGE via the Snowsight UI.
-- ============================================================
USE ROLE IPL_ENGINEER_ROLE;

-- ---------- 1. App stage (root location) ----------
CREATE OR REPLACE STAGE IPL_ANALYTICS_DB.GOLD.IPL_STREAMLIT_STAGE
    COMMENT = 'Root location for the IPL Streamlit app files';

-- ---------- 2. Streamlit app ----------
CREATE OR REPLACE STREAMLIT IPL_ANALYTICS_DB.GOLD.IPL_DASHBOARD
    ROOT_LOCATION    = '@IPL_ANALYTICS_DB.GOLD.IPL_STREAMLIT_STAGE'
    MAIN_FILE        = 'app.py'
    QUERY_WAREHOUSE  = IPL_QUERY_WH
    COMMENT          = 'IPL analytics dashboard on the GOLD layer';

-- ---------- 3. Sanity check ----------
SHOW STREAMLITS IN SCHEMA IPL_ANALYTICS_DB.GOLD;
