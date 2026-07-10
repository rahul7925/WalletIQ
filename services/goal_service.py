"""
goal_service.py — Backend Goal Services
Calculates required savings targets, inserts goals, updates goal history/progress,
and retrieves goal summaries for the logged-in user.
"""

from datetime import datetime, date
from app import db, Goal, GoalHistory, GoalProgress, ist_now
from services.goal_prediction_service import calculate_goal_progress_analytics

def create_user_goal(user_id: int, name: str, category: str, target_amount: float, current_savings: float, deadline_str: str, priority: str = 'Medium', notes: str = None) -> Goal:
    deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    
    # Calculate initial monthly contribution
    months_left = get_months_difference(ist_now().date(), deadline)
    if months_left <= 0:
        months_left = 1
    
    remaining = max(0.0, target_amount - current_savings)
    monthly_contribution = remaining / months_left

    goal = Goal(
        user_id=user_id,
        name=name,
        category=category,
        target_amount=target_amount,
        current_savings=current_savings,
        deadline=deadline,
        monthly_contribution=round(monthly_contribution, 2),
        priority=priority,
        status='Active',
        notes=notes
    )
    db.session.add(goal)
    db.session.commit()

    # Create initial progress record
    recalculate_goal_targets(goal.id)
    return goal

def update_user_goal_savings(goal_id: int, user_id: int, new_savings: float) -> Goal:
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return None

    # Track difference in goal history
    diff = new_savings - goal.current_savings
    if diff != 0:
        history_entry = GoalHistory(goal_id=goal.id, amount=diff)
        db.session.add(history_entry)

    goal.current_savings = new_savings
    if goal.current_savings >= goal.target_amount:
        goal.status = 'Completed'
    
    db.session.commit()
    recalculate_goal_targets(goal.id)
    return goal

def get_months_difference(date1: date, date2: date) -> int:
    return (date2.year - date1.year) * 12 + date2.month - date1.month

def recalculate_goal_targets(goal_id: int):
    goal = Goal.query.get(goal_id)
    if not goal:
        return

    today = ist_now().date()
    months_left = get_months_difference(today, goal.deadline)
    if months_left <= 0:
        months_left = 1

    remaining = max(0.0, goal.target_amount - goal.current_savings)
    goal.monthly_contribution = round(remaining / months_left, 2)
    db.session.commit()

    # Calculate weekly & daily targets
    # Assuming average of 4.33 weeks per month, and 30 days per month
    monthly_target = goal.monthly_contribution
    weekly_target = round(monthly_target / 4.33, 2)
    daily_target = round(monthly_target / 30.0, 2)

    # Use prediction service for advanced probability/completion date
    pred_data = calculate_goal_progress_analytics(goal)

    # Update or insert GoalProgress
    progress = GoalProgress.query.filter_by(goal_id=goal.id).first()
    if not progress:
        progress = GoalProgress(goal_id=goal.id)
        db.session.add(progress)

    progress.monthly_target = monthly_target
    progress.weekly_target = weekly_target
    progress.daily_target = daily_target
    progress.est_completion_date = pred_data.get('est_completion_date')
    progress.success_probability = pred_data.get('success_probability', 50.0)
    db.session.commit()
