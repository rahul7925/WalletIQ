"""
WalletIQ - Expense Predictor & Analytics
Linear Regression based next-expense forecasting (MySQL-backed)
"""

import os
import warnings
from datetime import datetime
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.linear_model import LinearRegression
from sqlalchemy import create_engine, text

warnings.filterwarnings('ignore')
load_dotenv()


def _mysql_engine():
    required = ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing MySQL env vars: {', '.join(missing)}")

    user = quote_plus(os.environ['MYSQL_USER'])
    pwd = quote_plus(os.environ['MYSQL_PASSWORD'])
    host = os.environ['MYSQL_HOST']
    port = int(os.environ['MYSQL_PORT'])
    db = os.environ['MYSQL_DATABASE']
    uri = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(uri, pool_pre_ping=True)


def main():
    try:
        engine = _mysql_engine()
        data = pd.read_sql_query(
            text("""
                SELECT id, title, amount, category, created_at
                FROM expense
                ORDER BY created_at ASC
            """),
            engine,
        )
    except Exception as e:
        print(f"DB Error: {e}")
        raise SystemExit(1) from e

    if data.empty:
        print("No expense data found. Add some expenses first.")
        raise SystemExit(0)

    print(f"Loaded {len(data)} expenses from database\n")
    print(data.to_string(index=False))

    data['day'] = range(1, len(data) + 1)
    data['created_at'] = pd.to_datetime(data['created_at'])
    data['dow'] = data['created_at'].dt.dayofweek
    data['month'] = data['created_at'].dt.month

    X = data[['day']]
    y = data['amount']
    model = LinearRegression()
    model.fit(X, y)

    next_day = len(data) + 1
    prediction = max(0, float(model.predict([[next_day]])[0]))

    print("\nExpense Summary by Category:")
    print("-" * 40)
    cat_summary = data.groupby('category')['amount'].agg(['sum', 'count', 'mean']).round(2)
    cat_summary.columns = ['Total (INR)', 'Count', 'Avg (INR)']
    cat_summary = cat_summary.sort_values('Total (INR)', ascending=False)
    print(cat_summary.to_string())

    if len(data) > 1:
        print("\nMonthly Spending Trend:")
        print("-" * 40)
        data['month_year'] = data['created_at'].dt.strftime('%b %Y')
        monthly = data.groupby('month_year')['amount'].sum().round(2)
        print(monthly.to_string())

    print("\nTop 5 Highest Expenses:")
    print("-" * 40)
    top5 = data.nlargest(5, 'amount')[['title', 'amount', 'category', 'created_at']]
    print(top5.to_string(index=False))

    print("\nSpending Statistics:")
    print("-" * 40)
    print(f"  Total Spent:    INR {data['amount'].sum():.2f}")
    print(f"  Average:        INR {data['amount'].mean():.2f}")
    print(f"  Highest:        INR {data['amount'].max():.2f}")
    print(f"  Lowest:         INR {data['amount'].min():.2f}")
    print(f"  Transactions:   {len(data)}")

    print(f"\nNext Predicted Expense: INR {prediction:.2f}")
    print(f"   Model R2 Score:        {model.score(X, y):.2%}")

    avg = data['amount'].mean()
    if prediction > avg * 1.5:
        print(f"\nALERT: Predicted expense is significantly above average (INR {avg:.2f})")
        print("   Consider reviewing your spending habits.")
    else:
        print("\nSpending appears to be within normal range.")


if __name__ == '__main__':
    main()
