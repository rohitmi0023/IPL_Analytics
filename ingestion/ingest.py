from argparse import ArgumentParser
import glob
import sys

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


def resolve_files(pattern: list[str]) -> list[str]:
    folder_path = f"{pattern[0]}/*.json"
    match_files = glob.glob(folder_path)
    return sorted(match_files)


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
    try:
        cur = conn.cursor()
        for file in files:
            cur.execute(
                f"PUT 'file://{file}' @{STAGE_NAME} "
                "OVERWRITE=FALSE AUTO_COMPRESS=FALSE"
            )
            print(f"PUT OK: {file}")
    finally:
        cur.close()
        return 
        


def main() -> int:
    parser = ArgumentParser(
        description="Ingest Cricsheet match JSON files from the given Folder location into Snowflake RAW layer."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One Folder paths/globs to match JSON files, e.g. data/year_2016",
    )
    args = parser.parse_args()
    files = resolve_files(args.paths)
    
    if not files:
        print(f"No files matched: {args.paths}")
        return 1

    conn = connect()
    try:
        errors = put_files(conn, files)
    finally:
        conn.close()

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())


