import pandas as pd
from db import pg_engine

AGGREGATION_SQL = """
SELECT
    p.product_name,
    DATE_TRUNC('month', o.created_at)::DATE  AS sale_month,
    SUM(oi.price_usd)                        AS revenue,
    COUNT(DISTINCT o.order_id)               AS order_count,
    SUM(oi.price_usd)
        / COUNT(DISTINCT o.order_id)         AS avg_order_value
FROM stg_orders o
JOIN stg_order_items oi  ON o.order_id    = oi.order_id
JOIN stg_products p      ON oi.product_id = p.product_id
GROUP BY
    p.product_name,
    DATE_TRUNC('month', o.created_at)::DATE
ORDER BY sale_month, product_name
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
