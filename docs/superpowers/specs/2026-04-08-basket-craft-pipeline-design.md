# Basket Craft Sales Pipeline — Design Spec

**Date:** 2026-04-08  
**Project:** ISBA 4715 — basket-craft-pipeline  
**Author:** Victor Sofelkanik  

---

## Overview

A monthly ELT data pipeline that extracts sales data from the Basket Craft MySQL course database, loads raw copies into a local PostgreSQL instance running in Docker, and transforms them into a `sales_summary` table for a monthly sales dashboard.

**Dashboard metrics:** Revenue, order count, and average order value (AOV) — grouped by product category and month.

---

## Pipeline Diagram

```
┌──────────────────────────────────────┐
│           SOURCE: MySQL              │
│  orders · order_items                │
│  products · categories               │
└──────────────────┬───────────────────┘
                   │
          PHASE 1: EXTRACT
          (extract.py)
                   │
┌──────────────────▼───────────────────┐
│    PostgreSQL (Docker) — Staging     │
│  stg_orders · stg_order_items        │
│  stg_products · stg_categories       │
└──────────────────┬───────────────────┘
                   │
          PHASE 2: TRANSFORM
          (transform.py)
                   │
┌──────────────────▼───────────────────┐
│    PostgreSQL (Docker) — Final       │
│         sales_summary                │
│  category · month · revenue          │
│  order_count · avg_order_value       │
└──────────────────────────────────────┘
```

**Orchestration:** `pipeline.py` calls extract then transform in sequence. Triggered manually or via cron on the 1st of each month.

---

## Architecture

- **Pattern:** ELT (Extract → Load raw → Transform in-database)
- **Source:** MySQL (Basket Craft course database)
- **Destination:** PostgreSQL 16 running in Docker
- **Language:** Python 3 with SQLAlchemy and pandas
- **Reload strategy:** Truncate-before-load (idempotent — safe to rerun)

---

## File Structure

```
basket-craft-pipeline/
├── docker-compose.yml          # PostgreSQL container definition
├── .env                        # DB credentials (gitignored)
├── requirements.txt            # Python dependencies
│
├── pipeline.py                 # Entry point — runs extract then transform
├── extract.py                  # Reads 4 tables from MySQL, writes to PG staging
├── transform.py                # Runs aggregation SQL, writes to sales_summary
├── db.py                       # SQLAlchemy engine factory (reads from .env)
│
└── cron/
    └── monthly.sh              # Cron wrapper: activates venv, runs pipeline.py
```

---

## Docker Configuration

**`docker-compose.yml`**

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

Named volume `pg_data` persists data across container restarts.

---

## Credential Configuration

**`.env`** (gitignored — never commit)

```env
# MySQL source (Basket Craft course DB — credentials from instructor)
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

**`db.py`** — Connection factory

```python
from dotenv import load_dotenv
from sqlalchemy import create_engine
import os

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

---

## Table Schemas

### Staging Tables (PostgreSQL — loaded by `extract.py`)

Exact copies of MySQL source tables, truncated and reloaded each run.

**`stg_orders`**
| Column | Type |
|---|---|
| order_id | INTEGER (PK) |
| customer_id | INTEGER |
| order_date | DATE |
| status | VARCHAR |

**`stg_order_items`**
| Column | Type |
|---|---|
| order_item_id | INTEGER (PK) |
| order_id | INTEGER (FK → stg_orders) |
| product_id | INTEGER (FK → stg_products) |
| quantity | INTEGER |
| unit_price | NUMERIC(10,2) |

**`stg_products`**
| Column | Type |
|---|---|
| product_id | INTEGER (PK) |
| product_name | VARCHAR |
| category_id | INTEGER (FK → stg_categories) |

**`stg_categories`**
| Column | Type |
|---|---|
| category_id | INTEGER (PK) |
| category_name | VARCHAR |

### Final Table: `sales_summary` (loaded by `transform.py`)

| Column | Type | Description |
|---|---|---|
| category_name | VARCHAR | e.g. "Wicker Baskets" |
| sale_month | DATE | First day of month: 2024-01-01 |
| revenue | NUMERIC(12,2) | SUM(quantity × unit_price) |
| order_count | INTEGER | COUNT(DISTINCT order_id) |
| avg_order_value | NUMERIC(10,2) | revenue / order_count |

---

## Aggregation SQL

Runs inside PostgreSQL against the staging schema:

```sql
SELECT
    c.category_name,
    DATE_TRUNC('month', o.order_date)::DATE AS sale_month,
    SUM(oi.quantity * oi.unit_price)              AS revenue,
    COUNT(DISTINCT o.order_id)                    AS order_count,
    SUM(oi.quantity * oi.unit_price)
        / COUNT(DISTINCT o.order_id)              AS avg_order_value
FROM stg_orders o
JOIN stg_order_items oi  ON o.order_id   = oi.order_id
JOIN stg_products p      ON oi.product_id = p.product_id
JOIN stg_categories c    ON p.category_id = c.category_id
GROUP BY
    c.category_name,
    DATE_TRUNC('month', o.order_date)::DATE
ORDER BY sale_month, category_name;
```

All four tables are required: category names live in `stg_categories`, not in `stg_orders`.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| MySQL/PostgreSQL unreachable | Raise immediately with clear message — no silent retry |
| Staging table empty after extract | Abort before transform — empty staging + transform = silent data loss |
| Transform produces zero rows | Log warning and exit with non-zero code |
| Any unhandled exception | `pipeline.py` catches, logs timestamped error, exits non-zero (cron detects failure) |

**Reload strategy:** Both extract and transform use truncate-before-load. Running the pipeline twice produces identical results — no duplicate row accumulation.

---

## Testing Strategy

| Test | What to check |
|---|---|
| Smoke test | Run `db.py` directly — verify both MySQL and PostgreSQL connections succeed |
| Row count after extract | Each staging table has rows; zero rows = extraction failed |
| Spot-check summary | Multiple categories, months in expected range, revenue > 0, AOV = revenue / order_count |
| Idempotency | Run pipeline twice — row count in `sales_summary` identical both times |

---

## Scheduling

Manual run:
```bash
python pipeline.py
```

Cron (1st of each month at 6am):
```
0 6 1 * * /path/to/cron/monthly.sh >> /var/log/basket_craft_pipeline.log 2>&1
```

`monthly.sh` activates the virtual environment and runs `pipeline.py`. Both stdout and stderr are logged for post-run inspection.

---

## Dependencies (`requirements.txt`)

```
sqlalchemy
pymysql
psycopg2-binary
pandas
python-dotenv
```
