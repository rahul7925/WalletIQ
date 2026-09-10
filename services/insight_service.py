"""
insight_service.py — Premium Spending Patterns and Natural Language AI Analysis.
Provides detailed category ranks, heatmaps, duplicate subscriptions,
and anomaly detection.
"""

from collections import defaultdict
from datetime import datetime, date
from app import db, User, Expense, ist_now

def generate_spending_insights_data(user_id: int) -> dict:
    now = ist_now()
    expenses = Expense.query.filter_by(user_id=user_id).all()
    
    this_month = [e for e in expenses if e.created_at.month == now.month and e.created_at.year == now.year]
    last_month = [e for e in expenses if e.created_at.month == (now.month - 1 if now.month > 1 else 12)
                  and e.created_at.year == (now.year if now.month > 1 else now.year - 1)]

    total_this = sum(e.amount for e in this_month)
    total_last = sum(e.amount for e in last_month)

    # 1. Category Rank
    cat_this = defaultdict(float)
    for e in this_month:
        cat_this[e.category] += e.amount

    cat_last = defaultdict(float)
    for e in last_month:
        cat_last[e.category] += e.amount

    ranked_categories = sorted(cat_this.items(), key=lambda x: -x[1])

    # 2. Fastest Growing Category
    fastest_growing = "None"
    max_growth = -1.0
    for cat, amt in cat_this.items():
        prev_amt = cat_last.get(cat, 0.0)
        if prev_amt > 0:
            growth = ((amt - prev_amt) / prev_amt) * 100.0
            if growth > max_growth:
                max_growth = growth
                fastest_growing = cat

    # 3. Duplicate Expenses / Subscription waste
    # Finds transactions with same title & amount repeating monthly
    titles = defaultdict(list)
    for e in expenses:
        titles[e.title.lower()].append(e)

    suspected_subscriptions = []
    for title, list_exp in titles.items():
        if len(list_exp) >= 2:
            amounts = [e.amount for e in list_exp]
            if len(set(amounts)) == 1:  # Identical recurring amounts
                suspected_subscriptions.append({
                    'title': list_exp[0].title,
                    'name': list_exp[0].title,
                    'amount': list_exp[0].amount,
                    'frequency': 'Monthly',
                    'total_waste': sum(amounts)
                })

    # 4. Heatmap Data (spending by day of week)
    dow_spending = defaultdict(float)
    for e in this_month:
        day_name = e.created_at.strftime('%A')
        dow_spending[day_name] += e.amount

    # 5. Average Daily vs Weekend Spending
    weekday_total = 0.0
    weekday_count = 0
    weekend_total = 0.0
    weekend_count = 0
    
    for e in this_month:
        if e.created_at.weekday() >= 5:  # Sat & Sun
            weekend_total += e.amount
            weekend_count += 1
        else:
            weekday_total += e.amount
            weekday_count += 1

    # 6. Anomalies & Recommendations
    anomalies = []
    recommendations = []

    if max_growth >= 30.0 and fastest_growing != "None":
        anomalies.append(f"High spending surge in {fastest_growing}: up +{round(max_growth, 1)}% vs last month.")
        recommendations.append(f"Consider capping non-essential purchases in {fastest_growing} to stabilize cash flow.")

    if suspected_subscriptions:
        total_sub_cost = sum(s['amount'] for s in suspected_subscriptions)
        anomalies.append(f"{len(suspected_subscriptions)} recurring subscription(s) detected costing ~₹{round(total_sub_cost, 2)}/mo.")
        recommendations.append(f"Audit {len(suspected_subscriptions)} suspected subscriptions for potential unused memberships.")

    if total_last > 0 and total_this > total_last * 1.25:
        spike_pct = round(((total_this - total_last) / total_last) * 100.0, 1)
        anomalies.append(f"Overall monthly outflow is pacing {spike_pct}% above last month's run rate.")

    if weekend_count > 0 and weekday_count > 0:
        avg_weekend = weekend_total / weekend_count
        avg_weekday = weekday_total / weekday_count
        if avg_weekend > avg_weekday * 1.5:
            ratio = round(avg_weekend / max(1.0, avg_weekday), 1)
            recommendations.append(f"Weekend expenditures are {ratio}x higher per day than weekdays. Consider a weekend dining envelope.")

    if not recommendations:
        recommendations.append("Spending patterns are within healthy baseline tolerances. Keep maintaining regular savings contributions.")

    return {
        'total_this_month': round(total_this, 2),
        'total_last_month': round(total_last, 2),
        'percentage_change': round(((total_this - total_last) / total_last * 100.0) if total_last > 0 else 0.0, 2),
        'ranked_categories': [{'category': k, 'amount': round(v, 2)} for k, v in ranked_categories],
        'fastest_growing_category': fastest_growing,
        'fastest_growing_percentage': round(max_growth, 2) if max_growth > 0 else 0.0,
        'suspected_subscriptions': suspected_subscriptions[:5],
        'subscriptions': suspected_subscriptions[:5],
        'heatmap': dict(dow_spending),
        'average_weekend': round(weekend_total / max(1, weekend_count), 2),
        'average_weekday': round(weekday_total / max(1, weekday_count), 2),
        'anomalies': anomalies,
        'recommendations': recommendations
    }
