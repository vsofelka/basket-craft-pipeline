# Basket Craft Pipeline

A monthly ELT data pipeline that extracts sales data from the Basket Craft MySQL database, loads it into a local PostgreSQL instance running in Docker, and aggregates it into a `sales_summary` table for a monthly sales dashboard.

**Dashboard metrics:** Revenue, order count, and average order value — grouped by product and month.

---

## How It Works

```
MySQL (source)
  orders, order_items, products
        │
        │  extract.py — reads source tables via SQLAlchemy
        ▼
PostgreSQL / Docker (staging)
  stg_orders, stg_order_items, stg_products
        │
        │  transform.py — aggregation SQL
        ▼
PostgreSQL / Docker (final)
  sales_summary
  (product_name · sale_month · revenue · order_count · avg_order_value)
```

Both phases use truncate-before-load, so the pipeline is safe to rerun.

---

## Prerequisites

- Python 3.9+
- Docker Desktop (running)
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

Edit `.env` and fill in your MySQL password. The file looks like this:

```env
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_DATABASE=basket_craft
MYSQL_USER=analyst
MYSQL_PASSWORD=your_password_here

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=basket_craft_dw
POSTGRES_USER=pipeline
POSTGRES_PASSWORD=pipeline_secret
```

**4. Start the PostgreSQL container**

```bash
docker compose up -d
```

---

## Running the Pipeline

```bash
# Windows
.venv\Scripts\python pipeline.py

# Mac / Linux
python pipeline.py
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

## Querying the Results

Connect to PostgreSQL and query `sales_summary`:

```bash
docker exec basket_craft_pg psql -U pipeline -d basket_craft_dw
```

```sql
-- Monthly revenue by product
SELECT product_name, sale_month, revenue, order_count, avg_order_value
FROM sales_summary
ORDER BY sale_month, product_name;

-- Top month by revenue
SELECT sale_month, SUM(revenue) AS total_revenue
FROM sales_summary
GROUP BY sale_month
ORDER BY total_revenue DESC
LIMIT 5;
```

---

## Running Tests

Both databases must be reachable before running tests.

```bash
# All tests
.venv\Scripts\pytest -v

# Single test
.venv\Scripts\pytest tests/test_db.py::test_mysql_connection -v
```

---

## Scheduling (Optional)

To run automatically on the 1st of each month, add this to your crontab (`crontab -e`):

```
0 6 1 * * /absolute/path/to/basket-craft-pipeline/cron/monthly.sh >> /var/log/basket_craft_pipeline.log 2>&1
```
