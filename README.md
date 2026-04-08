# Basket Craft Pipeline

An ELT data pipeline that extracts sales data from the Basket Craft MySQL database and loads it into two destinations: a local Docker PostgreSQL for a monthly sales dashboard, and an AWS RDS PostgreSQL as a cloud data warehouse with all raw tables.

---

## How It Works

```
MySQL (source) — 8 tables
        │
        ├─── extract_to_rds.py ──────────────────────────────────────►  AWS RDS PostgreSQL
        │    all 8 tables, raw, no transformations                       (basket_craft DB)
        │
        └─── extract.py ──► Docker PostgreSQL (staging) ──► transform.py ──► sales_summary
             orders,              stg_orders,                  aggregation SQL    product · month ·
             order_items,         stg_order_items,             by product/month   revenue · AOV
             products             stg_products
```

Both pipelines use truncate-before-load and are safe to rerun.

---

## Prerequisites

- Python 3.9+
- Docker Desktop (for local pipeline)
- AWS CLI configured (`aws configure`) with access to the `us-east-2` region
- MySQL credentials from your instructor

---

## Setup

**1. Clone the repo and create a virtual environment**

```bash
git clone https://github.com/vsofelka/basket-craft-pipeline.git
cd basket-craft-pipeline
python -m venv .venv
```

**2. Install dependencies**

```bash
# Windows
.venv\Scripts\pip install -r requirements.txt

# Mac / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Configure credentials**

```bash
cp .env.example .env
```

Edit `.env` and fill in your passwords:

```env
# MySQL source
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_DATABASE=basket_craft
MYSQL_USER=analyst
MYSQL_PASSWORD=your_password_here

# Local Docker PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=basket_craft_dw
POSTGRES_USER=pipeline
POSTGRES_PASSWORD=pipeline_secret

# AWS RDS PostgreSQL
RDS_HOST=basket-craft-db.c76css2awzb4.us-east-2.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=basket_craft
RDS_USER=student
RDS_PASSWORD=your_rds_password_here
```

**4. Start the local Docker PostgreSQL container**

```bash
docker compose up -d
```

---

## Pipelines

### Pipeline 1 — Raw load to AWS RDS

Loads all 8 Basket Craft tables from MySQL into AWS RDS as-is. No transformations.

```bash
.venv\Scripts\python extract_to_rds.py   # Windows
python extract_to_rds.py                 # Mac / Linux
```

Tables loaded: `employees`, `order_item_refunds`, `order_items`, `orders`, `products`, `users`, `website_pageviews`, `website_sessions`

### Pipeline 2 — Local dashboard pipeline

Extracts 3 tables from MySQL into Docker PostgreSQL staging, then aggregates into `sales_summary`.

```bash
.venv\Scripts\python pipeline.py   # Windows
python pipeline.py                 # Mac / Linux
```

Expected output:
```
[2026-04-08 06:00:00] Pipeline starting
[2026-04-08 06:00:00] Phase 1: Extracting from MySQL...
  orders: 32313 rows loaded to stg_orders
  order_items: 40025 rows loaded to stg_order_items
  products: 4 rows loaded to stg_products
[2026-04-08 06:00:12] Phase 2: Transforming in PostgreSQL...
  sales_summary: 94 rows written
[2026-04-08 06:00:13] Pipeline complete
```

---

## Querying the Data

**Local Docker (`sales_summary`):**

```bash
docker exec basket_craft_pg psql -U pipeline -d basket_craft_dw
```

```sql
SELECT product_name, sale_month, revenue, order_count, avg_order_value
FROM sales_summary
ORDER BY sale_month, product_name;
```

**AWS RDS (raw tables):** Connect via DBeaver or psql using the RDS endpoint, port 5432, database `basket_craft`, username `student`.

---

## Running Tests

Both MySQL and local Docker PostgreSQL must be reachable.

```bash
.venv\Scripts\pytest -v                                          # all tests
.venv\Scripts\pytest tests/test_db.py::test_mysql_connection -v # single test
```

---

## Scheduling (Optional)

To run the local dashboard pipeline on the 1st of each month:

```
0 6 1 * * /absolute/path/to/basket-craft-pipeline/cron/monthly.sh >> /var/log/basket_craft_pipeline.log 2>&1
```
