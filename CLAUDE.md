# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Use a Python virtual environment to manage dependencies:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # Mac/Linux
```

Credentials are read from `.env` (gitignored). Copy `.env.example` and fill in values. The `.env` file holds three sets of credentials: MySQL source, local Docker PostgreSQL, and AWS RDS PostgreSQL.

The local Docker PostgreSQL runs via:

```bash
docker compose up -d        # start container
docker compose down         # stop (data persists in named volume pg_data)
```

## Common Commands

```bash
# Load all 8 raw MySQL tables into AWS RDS (Session 02 raw load)
.venv/Scripts/python extract_to_rds.py

# Run the local dashboard pipeline (extract 3 tables + aggregate → sales_summary)
.venv/Scripts/python pipeline.py

# Run only extraction to local Docker PostgreSQL staging
.venv/Scripts/python extract.py

# Run only transformation (staging → sales_summary)
.venv/Scripts/python transform.py

# Run all tests
.venv/Scripts/pytest -v

# Run a single test
.venv/Scripts/pytest tests/test_db.py::test_mysql_connection -v

# Inspect local PostgreSQL via psql
docker exec basket_craft_pg psql -U pipeline -d basket_craft_dw
```

## Architecture

This project has two separate pipelines sharing the same source (Basket Craft MySQL) and the same connection factory (`db.py`).

**Pipeline 1 — Raw load to AWS RDS** (`extract_to_rds.py`): Loads all 8 MySQL tables as-is into AWS RDS PostgreSQL with no transformations. This is the cloud data warehouse raw layer, used as the source for future dbt transformations (Session 03+).

**Pipeline 2 — Local dashboard pipeline** (`pipeline.py`): Two-phase ELT into local Docker PostgreSQL. `extract.py` loads 3 tables (`orders`, `order_items`, `products`) into staging. `transform.py` aggregates them into `sales_summary` by product and month. Triggered manually or via cron.

**Connection factory** (`db.py`): Three engine functions — `mysql_engine()` (source), `pg_engine()` (local Docker), `rds_engine()` (AWS RDS). All credentials from `.env` via `python-dotenv`.

## Destinations

| Destination | Purpose | Script |
|---|---|---|
| Local Docker PostgreSQL | Dashboard staging + `sales_summary` | `pipeline.py` |
| AWS RDS (`basket-craft-db`, `us-east-2`) | Raw data warehouse | `extract_to_rds.py` |

AWS RDS endpoint: `basket-craft-db.c76css2awzb4.us-east-2.rds.amazonaws.com`  
RDS database: `basket_craft` · username: `student`

## Key Schema Details

**MySQL source** (8 tables): `orders` (32k), `order_items` (40k), `order_item_refunds` (1.7k), `products` (4), `employees` (20), `users` (31k), `website_sessions` (473k), `website_pageviews` (1.2M).

No `categories` table exists — the local pipeline groups by `product_name`. Revenue is `order_items.price_usd`. Dates are `created_at` timestamps.

**`sales_summary`** columns: `product_name`, `sale_month` (DATE, first of month), `revenue`, `order_count`, `avg_order_value`.

## Tests

All tests are integration tests — MySQL and local Docker PostgreSQL must both be reachable. Tests cover connection smoke tests, staging row counts, `sales_summary` structure and AOV math, and pipeline idempotency.
