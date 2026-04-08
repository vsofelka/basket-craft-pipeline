import sys
from datetime import datetime
from extract import extract
from transform import transform


def _log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}")


def run():
    _log("Pipeline starting")
    try:
        _log("Phase 1: Extracting from MySQL...")
        extract()
        _log("Phase 2: Transforming in PostgreSQL...")
        transform()
        _log("Pipeline complete")
    except Exception as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    run()
