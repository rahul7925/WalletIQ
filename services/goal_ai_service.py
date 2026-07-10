"""
goal_ai_service.py — Links active savings goals to AI spending recommendations.
Generates a concrete action plan to find savings in budgets to fund goals.
"""

from app import db, Goal, GoalRecommendations, Budget, Expense, ist_now

def generate_goal_ai_recommendations(user_id: int, goal_id: int) -> list:
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return []

    # Get active budgets and monthly average spending
    now = ist_now()
    expenses = Expense.query.filter_by(user_id=user_id).all()
    this_month_expenses = [e for e in expenses if e.created_at.month == now.month and e.created_at.year == now.year]
    
    cat_totals = {}
    for e in this_month_expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0.0) + e.amount

    # AI strategy: find discretionary categories (Food, Shopping, Entertainment) and recommend 10% reductions
    actions = []
    
    target_reduction = goal.monthly_contribution
    reduced_so_far = 0.0

    discretionary_categories = ['Food', 'Shopping', 'Entertainment', 'Travel']
    for cat in discretionary_categories:
        spent = cat_totals.get(cat, 0.0)
        if spent > 2000.0:
            reduction = min(spent * 0.15, target_reduction - reduced_so_far)
            if reduction > 100.0:
                action_text = f"Reduce discretionary spend in '{cat}' by ₹{int(reduction):,} (currently spending ₹{int(spent):,})"
                actions.append({
                    'action': action_text,
                    'impact_amount': round(reduction, 2)
                })
                reduced_so_far += reduction
                if reduced_so_far >= target_reduction:
                    break

    # If still short, recommend direct SIP reallocation or generic action step
    if reduced_so_far < target_reduction:
        leftover = target_reduction - reduced_so_far
        action_text = f"Automate monthly transfer of ₹{int(leftover):,} from salary account on payday."
        actions.append({
            'action': action_text,
            'impact_amount': round(leftover, 2)
        })

    # Save to database
    # Clear old recommendations for this goal first
    GoalRecommendations.query.filter_by(goal_id=goal_id).delete()
    for a in actions:
        db_reco = GoalRecommendations(
            user_id=user_id,
            goal_id=goal_id,
            action=a['action'],
            impact_amount=a['impact_amount']
        )
        db.session.add(db_reco)
    db.session.commit()

    return actions
