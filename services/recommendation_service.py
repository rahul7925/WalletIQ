"""
recommendation_service.py — AI Financial Recommendations Engine
Suggests optimal budgets, savings opportunities, and alerts.
"""

from app import db, User, RecommendationHistory, ist_now
from services.insight_service import generate_spending_insights_data

def generate_user_recommendations(user_id: int) -> list:
    insights = generate_spending_insights_data(user_id)
    recos = []

    # Recommendation 1: Fastest growing spending category
    if insights['fastest_growing_category'] != "None" and insights['fastest_growing_percentage'] > 15.0:
        msg = f"Your spending in '{insights['fastest_growing_category']}' grew by {insights['fastest_growing_percentage']}% compared to last month. We recommend cutting back discretionary spending in this category by 15%."
        recos.append({'category': 'Budget adjustment', 'message': msg, 'potential_savings': insights['total_this_month'] * 0.05})

    # Recommendation 2: Duplicate subscription waste
    for sub in insights['suspected_subscriptions']:
        if sub['amount'] > 499.0:
            msg = f"Potential subscription waste detected: you paid ₹{int(sub['amount']):,} multiple times for '{sub['title']}'. Consider canceling duplicate subscriptions."
            recos.append({'category': 'Cost-cutting', 'message': msg, 'potential_savings': sub['amount']})

    # Recommendation 3: Weekend spike
    if insights['average_weekend'] > insights['average_weekday'] * 1.5:
        msg = f"Weekend spending spikes detected (avg ₹{int(insights['average_weekend']):,} vs weekday avg ₹{int(insights['average_weekday']):,}). Try setting a weekend allowance of ₹{int(insights['average_weekday'] * 1.2):,}."
        recos.append({'category': 'Saving', 'message': msg, 'potential_savings': (insights['average_weekend'] - insights['average_weekday']) * 4})

    # Default fallback recommendations if profiles are clean
    if not recos:
        recos.append({
            'category': 'Saving',
            'message': "Shift at least 5% of your unused cash balance into active mutual fund SIPs to fight inflation.",
            'potential_savings': 2000.0
        })
        recos.append({
            'category': 'Budget adjustment',
            'message': "Review your 'General' category expenses and assign specific labels to track them better.",
            'potential_savings': 500.0
        })

    # Store in DB RecommendationHistory
    for r in recos:
        existing = RecommendationHistory.query.filter_by(user_id=user_id, message=r['message']).first()
        if not existing:
            db_reco = RecommendationHistory(
                user_id=user_id,
                category=r['category'],
                message=r['message'],
                potential_savings=r['potential_savings']
            )
            db.session.add(db_reco)
    db.session.commit()

    return recos
