import pandas as pd
from db import mysql_engine, rds_engine

TABLES = [
    'employees',
    'order_item_refunds',
    'order_items',
    'orders',
    'products',
    'users',
    'website_pageviews',
    'website_sessions',
]


def extract_to_rds():
    mysql = mysql_engine()
    rds = rds_engine()

    for table in TABLES:
        df = pd.read_sql(f"SELECT * FROM {table}", mysql)
        if df.empty:
            raise ValueError(f"Source table '{table}' is empty — aborting")
        df.to_sql(table, rds, if_exists='replace', index=False)
        print(f"  {table}: {len(df)} rows loaded")

    mysql.dispose()
    rds.dispose()
    print("Done.")


if __name__ == '__main__':
    extract_to_rds()
