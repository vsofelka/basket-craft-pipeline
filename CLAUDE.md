# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Use a Python virtual environment to manage dependencies:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # Mac/Linux
```

Credentials are read from `.env` (gitignored). Copy `.env.example` and fill in values.

The PostgreSQL destination runs in Docker:

```bash
docker compose up -d        # start container
docker compose down         # stop (data persists in named volume pg_data)
```

## Common Commands

```bash
# Run the full pipeline (extract + transform)
.venv/Scripts/python pipeline.py

# Run only extraction (MySQL → PostgreSQL staging)
.venv/Scripts/python extract.py

# Run only transformation (staging → sales_summary)
.venv/Scripts/python transform.py

# Run all tests
.venv/Scripts/pytest -v

# Run a single test
.venv/Scripts/pytest tests/test_db.py::test_mysql_connection -v

# Inspect PostgreSQL via psql
docker exec basket_craft_pg psql -U pipeline -d basket_craft_dw
```

## Architecture

Two-phase ELT pipeline: MySQL (source) → PostgreSQL (destination).

**Phase 1 — Extract** (`extract.py`): Reads `orders`, `order_items`, and `products` from the Basket Craft MySQL database using SQLAlchemy + pandas. Each table is truncated and reloaded as `stg_orders`, `stg_order_items`, `stg_products` in PostgreSQL. Aborts if any source table is empty.

**Phase 2 — Transform** (`transform.py`): Runs an aggregation SQL query inside PostgreSQL joining the three staging tables. Produces `sales_summary` with monthly revenue, order count, and average order value grouped by `product_name`. Also truncate-before-load.

**Orchestrator** (`pipeline.py`): Calls `extract()` then `transform()` in sequence. Catches all exceptions, logs with timestamps, exits non-zero on failure (cron-safe).

**Connection factory** (`db.py`): Returns SQLAlchemy engines for MySQL (`mysql_engine()`) and PostgreSQL (`pg_engine()`). All credentials come from environment variables loaded via `python-dotenv`.

## Key Schema Details

MySQL source tables: `orders` (32k rows), `order_items` (40k rows), `products` (4 rows). There is no `categories` table — grouping is by `product_name`. Revenue is `order_items.price_usd` (not quantity × unit_price). Dates are `created_at` timestamps (not `order_date`).

`sales_summary` columns: `product_name`, `sale_month` (DATE, first of month), `revenue`, `order_count`, `avg_order_value`.

## Tests

All tests are integration tests — both MySQL and PostgreSQL must be reachable before running. Tests cover connection smoke tests, staging row counts, `sales_summary` structure and AOV math, and pipeline idempotency.
