import pandas as pd
from db import mysql_engine, pg_engine

TABLES = ['orders', 'order_items', 'products']


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
