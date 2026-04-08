# Basket Craft Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an ELT pipeline that extracts Basket Craft sales data from MySQL, loads raw tables into a local PostgreSQL Docker container, and aggregates them into a `sales_summary` table by product category and month.

**Architecture:** Python scripts orchestrated by `pipeline.py` in two phases: `extract.py` reads four MySQL tables and writes them as staging tables to PostgreSQL; `transform.py` runs a SQL aggregation joining all four staging tables to produce `sales_summary`. Both phases use truncate-before-load for idempotency.

**Tech Stack:** Python 3, SQLAlchemy, pandas, pymysql, psycopg2-binary, python-dotenv, PostgreSQL 16 (Docker), pytest

---

## File Map

| File | Responsibility |
|---|---|
| `docker-compose.yml` | PostgreSQL 16 container with named volume |
| `.env.example` | Credential template (committed); `.env` is gitignored |
| `requirements.txt` | Python dependencies |
| `pytest.ini` | Pytest config — adds project root to Python path |
| `db.py` | SQLAlchemy engine factory for MySQL and PostgreSQL |
| `extract.py` | Reads 4 MySQL tables, writes to PostgreSQL staging |
| `transform.py` | Aggregation SQL → writes `sales_summary` |
| `pipeline.py` | Orchestrates extract → transform, error handling, exit codes |
| `cron/monthly.sh` | Shell wrapper for cron scheduling |
| `tests/test_db.py` | Integration: both DB connections succeed |
| `tests/test_extract.py` | Integration: staging tables populated with rows |
| `tests/test_transform.py` | Integration: `sales_summary` has correct structure and values |
| `tests/test_pipeline.py` | Integration: pipeline is idempotent |

> **Note:** All tests are integration tests — they require both MySQL (course DB) and PostgreSQL (Docker) to be reachable. Run `docker compose up -d` before running any tests.

---

## Task 1: Project Scaffold

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `pytest.ini`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    container_name: basket_craft_pg
    restart: unless-stopped
    environment:
      POSTGRES_DB:       ${POSTGRES_DB}
      POSTGRES_USER:     ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

- [ ] **Step 2: Create `.env.example`**

```env
# MySQL source (Basket Craft course DB — get password from instructor)
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_DATABASE=basket_craft
MYSQL_USER=analyst
MYSQL_PASSWORD=<from_instructor>

# PostgreSQL destination (local Docker)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=basket_craft_dw
POSTGRES_USER=pipeline
POSTGRES_PASSWORD=pipeline_secret
```

- [ ] **Step 3: Copy `.env.example` to `.env` and fill in `MYSQL_PASSWORD`**

```bash
cp .env.example .env
# Edit .env and replace <from_instructor> with the real MySQL password
```

- [ ] **Step 4: Create `requirements.txt`**

```
sqlalchemy
pymysql
psycopg2-binary
pandas
python-dotenv
pytest
```

- [ ] **Step 5: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

This tells pytest to look for tests in `tests/` and adds the project root to `sys.path` so `import db`, `import extract`, etc. work without installing the package.

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: no errors. If `psycopg2-binary` fails on Windows, try `pip install psycopg2-binary --only-binary=all`.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .env.example requirements.txt pytest.ini
git commit -m "feat: add project scaffold — docker, deps, pytest config"
```

---

## Task 2: Start PostgreSQL Container

**Files:** (no code changes — just infrastructure verification)

- [ ] **Step 1: Start the container**

```bash
docker compose up -d
```

Expected output (last line): `Container basket_craft_pg  Started`

- [ ] **Step 2: Verify PostgreSQL is ready**

```bash
docker exec basket_craft_pg pg_isready -U pipeline
```

Expected: `localhost:5432 - accepting connections`

If it says `no response`, wait 5 seconds and retry — PostgreSQL takes a moment to initialize on first start.

- [ ] **Step 3: Verify named volume exists**

```bash
docker volume ls | grep pg_data
```

Expected: a line containing `basket-craft-pipeline_pg_data`

---

## Task 3: `db.py` — Connection Factory

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Create `tests/` directory and write the failing tests**

```bash
mkdir tests
```

Create `tests/test_db.py`:

```python
from sqlalchemy import text
from db import mysql_engine, pg_engine


def test_mysql_connection():
    engine = mysql_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    engine.dispose()


def test_pg_connection():
    engine = pg_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    engine.dispose()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: `ImportError: No module named 'db'` (db.py doesn't exist yet)

- [ ] **Step 3: Create `db.py`**

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


def mysql_engine():
    url = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
        f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    )
    return create_engine(url)


def pg_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )
    return create_engine(url)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected:
```
tests/test_db.py::test_mysql_connection PASSED
tests/test_db.py::test_pg_connection PASSED
```

If `test_mysql_connection` fails with `OperationalError`, check that `MYSQL_PASSWORD` in `.env` has the real password from your instructor.

If `test_pg_connection` fails, check that the Docker container is running: `docker compose up -d`

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add db engine factory with connection tests"
```

---

## Task 4: `extract.py` — MySQL → PostgreSQL Staging

**Files:**
- Create: `extract.py`
- Create: `tests/test_extract.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_extract.py`:

```python
import pandas as pd
from sqlalchemy import text, inspect
from db import pg_engine
from extract import extract

STAGING_TABLES = [
    'stg_orders',
    'stg_order_items',
    'stg_products',
    'stg_categories',
]


def test_staging_tables_exist_after_extract():
    extract()
    pg = pg_engine()
    inspector = inspect(pg)
    existing = inspector.get_table_names()
    for table in STAGING_TABLES:
        assert table in existing, f"'{table}' not found in PostgreSQL after extract"
    pg.dispose()


def test_staging_tables_have_rows():
    pg = pg_engine()
    with pg.connect() as conn:
        for table in STAGING_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count > 0, f"'{table}' is empty after extract"
    pg.dispose()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_extract.py -v
```

Expected: `ImportError: No module named 'extract'`

- [ ] **Step 3: Create `extract.py`**

```python
import pandas as pd
from db import mysql_engine, pg_engine

TABLES = ['orders', 'order_items', 'products', 'categories']


def extract():
    mysql = mysql_engine()
    pg = pg_engine()

    for table in TABLES:
        df = pd.read_sql(f"SELECT * FROM {table}", mysql)
        if df.empty:
            raise ValueError(f"Extracted table '{table}' is empty — aborting before load")
        df.to_sql(f"stg_{table}", pg, if_exists='replace', index=False)
        print(f"  {table}: {len(df)} rows loaded to stg_{table}")

    mysql.dispose()
    pg.dispose()


if __name__ == '__main__':
    extract()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_extract.py -v
```

Expected:
```
tests/test_extract.py::test_staging_tables_exist_after_extract PASSED
tests/test_extract.py::test_staging_tables_have_rows PASSED
```

This step makes a real network call to the course MySQL database and loads data into Docker PostgreSQL. It will take a few seconds.

- [ ] **Step 5: Commit**

```bash
git add extract.py tests/test_extract.py
git commit -m "feat: add extract step — MySQL to PostgreSQL staging tables"
```

---

## Task 5: `transform.py` — Staging → `sales_summary`

**Files:**
- Create: `transform.py`
- Create: `tests/test_transform.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transform.py`:

```python
import pandas as pd
from sqlalchemy import text
from db import pg_engine
from transform import transform


def test_sales_summary_has_rows():
    transform()
    pg = pg_engine()
    with pg.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM sales_summary")).scalar()
        assert count > 0, "sales_summary is empty after transform"
    pg.dispose()


def test_sales_summary_has_correct_columns():
    pg = pg_engine()
    df = pd.read_sql("SELECT * FROM sales_summary LIMIT 1", pg)
    expected = {'category_name', 'sale_month', 'revenue', 'order_count', 'avg_order_value'}
    assert expected.issubset(set(df.columns)), f"Missing columns: {expected - set(df.columns)}"
    pg.dispose()


def test_aov_equals_revenue_divided_by_order_count():
    pg = pg_engine()
    df = pd.read_sql("SELECT * FROM sales_summary", pg)
    calculated = (df['revenue'] / df['order_count']).round(2)
    actual = df['avg_order_value'].round(2)
    assert (calculated == actual).all(), "avg_order_value does not equal revenue / order_count for all rows"
    pg.dispose()


def test_sales_summary_has_multiple_categories():
    pg = pg_engine()
    df = pd.read_sql("SELECT DISTINCT category_name FROM sales_summary", pg)
    assert len(df) > 1, f"Expected multiple categories, got: {df['category_name'].tolist()}"
    pg.dispose()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_transform.py -v
```

Expected: `ImportError: No module named 'transform'`

- [ ] **Step 3: Create `transform.py`**

```python
import pandas as pd
from db import pg_engine

AGGREGATION_SQL = """
SELECT
    c.category_name,
    DATE_TRUNC('month', o.order_date)::DATE AS sale_month,
    SUM(oi.quantity * oi.unit_price)              AS revenue,
    COUNT(DISTINCT o.order_id)                    AS order_count,
    SUM(oi.quantity * oi.unit_price)
        / COUNT(DISTINCT o.order_id)              AS avg_order_value
FROM stg_orders o
JOIN stg_order_items oi  ON o.order_id    = oi.order_id
JOIN stg_products p      ON oi.product_id = p.product_id
JOIN stg_categories c    ON p.category_id = c.category_id
GROUP BY
    c.category_name,
    DATE_TRUNC('month', o.order_date)::DATE
ORDER BY sale_month, category_name
"""


def transform():
    pg = pg_engine()
    df = pd.read_sql(AGGREGATION_SQL, pg)
    if df.empty:
        raise ValueError("Transform produced zero rows — check that staging tables are populated")
    df.to_sql('sales_summary', pg, if_exists='replace', index=False)
    print(f"  sales_summary: {len(df)} rows written")
    pg.dispose()


if __name__ == '__main__':
    transform()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_transform.py -v
```

Expected:
```
tests/test_transform.py::test_sales_summary_has_rows PASSED
tests/test_transform.py::test_sales_summary_has_correct_columns PASSED
tests/test_transform.py::test_aov_equals_revenue_divided_by_order_count PASSED
tests/test_transform.py::test_sales_summary_has_multiple_categories PASSED
```

If `test_aov_equals_revenue_divided_by_order_count` fails with floating-point mismatch, confirm PostgreSQL's `NUMERIC` division is consistent with pandas `.round(2)`. The test uses `.round(2)` on both sides to tolerate minor float drift.

- [ ] **Step 5: Commit**

```bash
git add transform.py tests/test_transform.py
git commit -m "feat: add transform step — aggregation SQL to sales_summary"
```

---

## Task 6: `pipeline.py` — Orchestrator

**Files:**
- Create: `pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline.py`:

```python
from sqlalchemy import text
from db import pg_engine
from pipeline import run


def test_pipeline_is_idempotent():
    run()
    pg = pg_engine()
    with pg.connect() as conn:
        count1 = conn.execute(text("SELECT COUNT(*) FROM sales_summary")).scalar()
    run()
    with pg.connect() as conn:
        count2 = conn.execute(text("SELECT COUNT(*) FROM sales_summary")).scalar()
    assert count1 == count2, (
        f"Pipeline is not idempotent — row count changed: {count1} → {count2}"
    )
    pg.dispose()
```

- [ ] **Step 2: Run test — verify it fails**

```bash
pytest tests/test_pipeline.py -v
```

Expected: `ImportError: No module named 'pipeline'`

- [ ] **Step 3: Create `pipeline.py`**

```python
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
```

- [ ] **Step 4: Run test — verify it passes**

```bash
pytest tests/test_pipeline.py -v
```

Expected:
```
tests/test_pipeline.py::test_pipeline_is_idempotent PASSED
```

This test runs the full pipeline twice and confirms the `sales_summary` row count is identical — proving truncate-before-load is working correctly.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests across `test_db.py`, `test_extract.py`, `test_transform.py`, `test_pipeline.py` pass.

- [ ] **Step 6: Commit**

```bash
git add pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator with idempotency test"
```

---

## Task 7: `cron/monthly.sh` — Scheduling Wrapper

**Files:**
- Create: `cron/monthly.sh`

- [ ] **Step 1: Create `cron/` directory and write `monthly.sh`**

```bash
mkdir cron
```

Create `cron/monthly.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Basket Craft pipeline"
python pipeline.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x cron/monthly.sh
```

- [ ] **Step 3: Test it manually**

```bash
bash cron/monthly.sh
```

Expected output:
```
[2026-04-08 HH:MM:SS] Starting Basket Craft pipeline
[2026-04-08 HH:MM:SS] Phase 1: Extracting from MySQL...
  orders: N rows loaded to stg_orders
  order_items: N rows loaded to stg_order_items
  products: N rows loaded to stg_products
  categories: N rows loaded to stg_categories
[2026-04-08 HH:MM:SS] Phase 2: Transforming in PostgreSQL...
  sales_summary: N rows written
[2026-04-08 HH:MM:SS] Pipeline complete
[2026-04-08 HH:MM:SS] Done
```

- [ ] **Step 4: Register the cron job (optional — for production use)**

Run `crontab -e` and add this line (replace the path with your actual project path):

```
0 6 1 * * /absolute/path/to/basket-craft-pipeline/cron/monthly.sh >> /var/log/basket_craft_pipeline.log 2>&1
```

This runs at 6am on the 1st of each month and logs all output (stdout + stderr) to a log file.

- [ ] **Step 5: Commit**

```bash
git add cron/monthly.sh
git commit -m "feat: add monthly cron wrapper script"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Covered by |
|---|---|
| Pipeline diagram (source → extract → transform → load → destination) | Design doc (ASCII diagram) — not a code artifact |
| File structure and script responsibilities | File Map table + Task 1 |
| Table schemas and SQL for aggregations | Tasks 4 and 5 |
| Docker and credential configuration | Task 1 (docker-compose.yml, .env.example) |
| Error handling | Task 6: pipeline.py catches + exits non-zero; extract.py raises on empty tables |
| Testing strategy | Tasks 3–6: integration tests for connections, row counts, AOV math, idempotency |
| Manual trigger | Task 6: `python pipeline.py` |
| Scheduled trigger | Task 7: `cron/monthly.sh` + crontab entry |

All spec requirements are covered. No gaps found.

### Placeholder scan

No TBDs, TODOs, or "similar to Task N" shortcuts. All code blocks are complete and self-contained.

### Type consistency

- `mysql_engine()` and `pg_engine()` defined in Task 3, used in Tasks 4, 5, 6 — consistent.
- `extract()` defined in Task 4, imported in Task 6 — consistent.
- `transform()` defined in Task 5, imported in Task 6 — consistent.
- `run()` defined in Task 6, called in Task 6's test — consistent.
- Staging table names `stg_orders`, `stg_order_items`, `stg_products`, `stg_categories` consistent across Task 4 extract and Task 5 SQL.
- `sales_summary` column names consistent between Task 5 SQL, Task 5 tests, and design spec.
