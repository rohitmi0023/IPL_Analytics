import argparse
import glob
import os
import sys
from pathlib import Path

import snowflake.connector

from config import (
    FILE_FORMAT,
    RAW_TABLE,
    STAGE_NAME,
    SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_PASSWORD,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_SCHEMA,
    SNOWFLAKE_USER,
    SNOWFLAKE_WAREHOUSE,
)


def match_id_from_filename(filename: str) -> str:
    return Path(filename).stem


def resolve_files(patterns: list[str]) -> list[str]:
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    return sorted(dict.fromkeys(files))


def connect():
    if not SNOWFLAKE_ACCOUNT or not SNOWFLAKE_PASSWORD:
        raise SystemExit(
            "Missing Snowflake credentials. Set SNOWFLAKE_ACCOUNT and "
            "SNOWFLAKE_PASSWORD in your .env file."
        )
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        role=SNOWFLAKE_ROLE,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
    )


def put_files(conn, files: list[str]) -> None:
    for file in files:
        local = file.replace("\\", "/")
        cur = conn.cursor()
        try:
#             PUT 'file:///Users/rohitmi/Downloads/IPL_Analytics/data/981017.json'
#               @IPL_ANALYTICS_DB.RAW.IPL_STAGE
#               OVERWRITE=TRUE AUTO_COMPRESS=FALSE;
            cur.execute(
                f"PUT 'file://{local}' @{STAGE_NAME} "
                "OVERWRITE=TRUE AUTO_COMPRESS=FALSE"
            )
            print(f"PUT OK: {file}")
        finally:
            cur.close()


def copy_files(conn, match_ids: list[str]) -> int:
    placeholders = ",".join(f"'{mid}'" for mid in match_ids)
    cur = conn.cursor()
    try:
        # DELETE FROM IPL_ANALYTICS_DB.RAW.RAW_MATCH_JSON WHERE match_id = '981017';
        cur.execute(f"DELETE FROM {RAW_TABLE} WHERE match_id IN ({placeholders})")
        deleted = cur.rowcount
        # COPY INTO IPL_ANALYTICS_DB.RAW.RAW_MATCH_JSON (match_id, file_name, raw_variant)
        # FROM (
        #     SELECT REGEXP_SUBSTR(metadata$filename, '([^/]+)\.json$', 1, 1, 'e', 1),
        #         metadata$filename,
        #         $1
        #     FROM @IPL_ANALYTICS_DB.RAW.IPL_STAGE
        # )
        # FILE_FORMAT = (FORMAT_NAME = 'IPL_ANALYTICS_DB.RAW.IPL_JSON_FORMAT');
        cur.execute(
            f"""
            COPY INTO {RAW_TABLE} (match_id, file_name, raw_variant)
            FROM (
                SELECT REGEXP_SUBSTR(metadata$filename, '([^/]+)\\.json$', 1, 1, 'e', 1),
                       metadata$filename,
                       $1
                FROM @{STAGE_NAME}
            )
            FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT}')
            """
        )
        loaded = 0
        errors = 0
        for row in cur:
            if row[1] == "LOADED":
                loaded += 1
            elif row[1] == "LOAD_FAILED":
                errors += 1
        print(f"COPY INTO complete: {loaded} loaded, {errors} failed (deleted {deleted} prior rows)")
        return errors
    finally:
        cur.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Cricsheet match JSON files into Snowflake RAW layer."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more paths/globs to match JSON files, e.g. data/981017.json",
    )
    args = parser.parse_args()

    files = resolve_files(args.paths)
    if not files:
        print(f"No files matched: {args.paths}")
        return 1

    conn = connect()
    try:
        put_files(conn, files)
        # match_ids = [match_id_from_filename(f) for f in files]
        # errors = copy_files(conn, match_ids)
    finally:
        conn.close()

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
