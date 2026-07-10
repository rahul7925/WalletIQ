"""
goal_notification_service.py — Evaluates goal targets and creates system alerts.
"""

from app import db, Goal, GoalNotifications, Notification, ist_now

def check_and_generate_goal_notifications(user_id: int):
    goals = Goal.query.filter_by(user_id=user_id, status='Active').all()
    for goal in goals:
        progress = goal.progress.first()
        if not progress:
            continue

        # Notification 1: Success probability below 60% (Adjustment recommended)
        if progress.success_probability < 60.0:
            msg = f"Your goal '{goal.name}' has a completion probability of {progress.success_probability}%. Consider increasing monthly savings by ₹{int(goal.monthly_contribution * 0.15):,} or extending the deadline."
            trigger_notification(user_id, goal.id, 'Adjustment Recommended', msg)

        # Notification 2: Milestone achieved
        pct = (goal.current_savings / goal.target_amount) * 100.0
        if pct >= 50.0 and pct < 51.0:
            msg = f"🎉 Milestone! You have saved 50% (₹{int(goal.current_savings):,}) of your target for '{goal.name}'!"
            trigger_notification(user_id, goal.id, 'Milestone Reached', msg)

def trigger_notification(user_id: int, goal_id: int, notif_type: str, message: str):
    # Check if duplicate notification in last 24h
    existing = GoalNotifications.query.filter_by(
        goal_id=goal_id, type=notif_type, message=message
    ).first()
    
    if not existing:
        notif = GoalNotifications(
            goal_id=goal_id,
            type=notif_type,
            message=message
        )
        db.session.add(notif)
        
        # Integrate with master Notification table
        master_notif = Notification(
            user_id=user_id,
            title=f"Goal Alert: {notif_type}",
            message=message,
            category='Savings',
            priority='High'
        )
        db.session.add(master_notif)
        db.session.commit()
