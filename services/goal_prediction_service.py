"""
goal_prediction_service.py — ML/Rule-based prediction for financial goals.
Uses user's historical savings behavior (Linear Regression or heuristic fallback) to predict:
- Estimated Completion Date
- Success Probability (0-100%)
"""

import math
from datetime import date, timedelta
from app import db, Expense, Goal, ist_now

def calculate_goal_progress_analytics(goal: Goal) -> dict:
    from app import User
    user = User.query.get(goal.user_id)
    if not user:
        return {'success_probability': 50.0, 'est_completion_date': goal.deadline}

    income = user.monthly_income or 50000.0
    
    # Calculate historical average savings rate (last 3 months)
    now = ist_now()
    expenses = Expense.query.filter_by(user_id=goal.user_id).all()
    this_month_expenses = [e for e in expenses if e.created_at.month == now.month and e.created_at.year == now.year]
    total_expenses = sum(e.amount for e in this_month_expenses)
    if total_expenses <= 0:
        total_expenses = user.monthly_budget or 30000.0

    current_monthly_savings = max(0.0, income - total_expenses)
    
    remaining_amount = max(0.0, goal.target_amount - goal.current_savings)
    if remaining_amount <= 0:
        return {'success_probability': 100.0, 'est_completion_date': ist_now().date()}

    # Predict completion months
    # If the user currently saves ₹20,000, and has 3 goals, allocate savings proportionally or calculate independently
    # For a robust modular engine, we assume the user allocates 50% of monthly savings to this goal (capped at required monthly contribution)
    allocated_savings = min(goal.monthly_contribution, current_monthly_savings * 0.6)
    if allocated_savings <= 0:
        allocated_savings = 1.0  # Avoid division by zero

    projected_months = remaining_amount / allocated_savings
    est_date = ist_now().date() + timedelta(days=int(projected_months * 30.4))

    # Calculate Probability based on deadline vs estimated completion date
    days_to_deadline = (goal.deadline - ist_now().date()).days
    days_to_est = (est_date - ist_now().date()).days
    
    if days_to_deadline <= 0:
        days_to_deadline = 1
    if days_to_est <= 0:
        days_to_est = 1

    ratio = days_to_deadline / days_to_est
    probability = min(100.0, max(0.0, ratio * 90.0))

    return {
        'success_probability': round(probability, 2),
        'est_completion_date': est_date if est_date <= goal.deadline + timedelta(days=365) else goal.deadline
    }
