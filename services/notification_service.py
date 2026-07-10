from datetime import date, timedelta
from app import db

def get_user_notifications(user_id: int) -> list:
    from app import Notification
    return Notification.query.filter_by(user_id=user_id, is_read=False, is_archived=False).order_by(Notification.created_at.desc()).all()

def mark_notification_read(user_id: int, notification_id: int) -> bool:
    from app import Notification
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return True
    return False

def mark_all_notifications_read(user_id: int) -> bool:
    from app import Notification
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    for n in notifications:
        n.is_read = True
    db.session.commit()
    return True

def archive_notification(user_id: int, notification_id: int) -> bool:
    from app import Notification
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif:
        notif.is_archived = True
        db.session.commit()
        return True
    return False

def generate_financial_alerts(user_id: int):
    """Dynamically evaluates user balance, subscriptions, expenses, and budget overruns, generating notifications"""
    from app import db, User, Expense, Budget, Bill, Notification, ist_now
    from services.financial_health import compute_financial_health
    
    now = ist_now()
    user = User.query.get(user_id)
    if not user:
        return
        
    health = compute_financial_health(user_id)
    income = health.get('income', 50000.0)
    expenses = health.get('expenses', 30000.0)
    # Estimated current balance = income - expenses
    current_balance = max(0.0, income - expenses)
    
    # 1. Low Balance Warning
    # Fetch unpaid bills due within the next 10 days
    unpaid_bills = Bill.query.filter_by(user_id=user_id, is_paid=False).all()
    upcoming_bill_total = 0.0
    for b in unpaid_bills:
        due_day = b.due_day
        # Determine if due day is within 10 days
        diff = due_day - now.day
        if 0 <= diff <= 10:
            upcoming_bill_total += b.amount
            
    if upcoming_bill_total > current_balance and upcoming_bill_total > 0:
        # Check if notification already exists
        exists = Notification.query.filter_by(user_id=user_id, category='Balance', is_read=False).first()
        if not exists:
            db.session.add(Notification(
                user_id=user_id,
                title="⚠️ Low Balance Warning",
                message=f"Your upcoming bills total ₹{upcoming_bill_total:,.2f} in the next 10 days, exceeding your estimated current balance of ₹{current_balance:,.2f}. Consider maintaining extra cash reserves.",
                category='Balance',
                priority='Critical'
            ))

    # 2. Duplicate Subscription Detection
    # Subscriptions categories
    sub_categories = ['Netflix', 'Spotify', 'Amazon Prime', 'ChatGPT Plus', 'Microsoft 365', 'Adobe', 'Gym Membership', 'Subscriptions']
    subs = [b for b in Bill.query.filter_by(user_id=user_id).all() if b.category in sub_categories or 'subscription' in b.name.lower()]
    if len(subs) >= 3:
        exists = Notification.query.filter_by(user_id=user_id, category='Savings', title="🔄 Duplicate/Multiple Subscriptions").first()
        if not exists:
            total_sub_cost = sum(s.amount for s in subs)
            db.session.add(Notification(
                user_id=user_id,
                title="🔄 Duplicate/Multiple Subscriptions",
                message=f"You currently have {len(subs)} active streaming/digital subscriptions costing ₹{total_sub_cost:,.2f}/month. Review and cancel any unused services to save money.",
                category='Savings',
                priority='Low'
            ))

    # 3. Budget Overspending Alerts
    budgets = Budget.query.filter_by(user_id=user_id, month=now.month, year=now.year).all()
    # Calculate spending by category this month
    all_expenses = Expense.query.filter_by(user_id=user_id).all()
    this_month_expenses = [e for e in all_expenses if e.created_at.month == now.month and e.created_at.year == now.year]
    cat_totals = {}
    for e in this_month_expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0.0) + e.amount

    for b in budgets:
        spent = cat_totals.get(b.category, 0.0)
        pct = (spent / b.amount) * 100.0 if b.amount > 0 else 0.0
        if pct >= 80.0:
            exists = Notification.query.filter_by(user_id=user_id, category='Budget', title=f"⚠️ Overspending Alert: {b.category}").first()
            if not exists:
                db.session.add(Notification(
                    user_id=user_id,
                    title=f"⚠️ Overspending Alert: {b.category}",
                    message=f"You have spent {pct:.1f}% of your ₹{b.amount:,.2f} budget for {b.category}. Consider pausing discretionary purchases in this category.",
                    category='Budget',
                    priority='High' if pct >= 100.0 else 'Medium'
                ))

    # 4. Spike Alerts
    # Analyze if food/shopping category spending spiked by > 40% compared to average weekly spending
    # Let's count recent expenses
    one_week_ago = now - timedelta(days=7)
    this_week_expenses = [e for e in this_month_expenses if e.created_at >= one_week_ago]
    week_totals = {}
    for e in this_week_expenses:
        week_totals[e.category] = week_totals.get(e.category, 0.0) + e.amount
        
    for cat, week_total in week_totals.items():
        if cat == 'Salary' or cat == 'Savings':
            continue
        # Average weekly spend
        cat_expenses = [e for e in all_expenses if e.category == cat]
        if len(cat_expenses) > 5:
            avg_weekly = sum(e.amount for e in cat_expenses) / (len(cat_expenses) / 4.0 or 1.0) # approx weeks
            if week_total > avg_weekly * 1.4:
                exists = Notification.query.filter_by(user_id=user_id, category='Spike', title=f"📈 Expense Spike: {cat}").first()
                if not exists:
                    db.session.add(Notification(
                        user_id=user_id,
                        title=f"📈 Expense Spike: {cat}",
                        message=f"Your {cat} expenses reached ₹{week_total:,.2f} this week, which is {(week_total/avg_weekly - 1.0)*100.0:.0f}% higher than your average weekly spending of ₹{avg_weekly:,.2f}.",
                        category='Spike',
                        priority='Medium'
                    ))

    # 5. Dynamic Bill Due alerts
    all_bills = Bill.query.filter_by(user_id=user_id, is_paid=False).all()
    for b in all_bills:
        diff = b.due_day - now.day
        if 0 <= diff <= 3:
            # Urgent Bill Reminder
            exists = Notification.query.filter_by(user_id=user_id, category='Bill', bill_id=b.id, is_read=False).first()
            if not exists:
                priority = 'Critical' if b.priority in ['Critical', 'High'] or b.category in ['Credit Card', 'EMI'] else 'High'
                db.session.add(Notification(
                    user_id=user_id,
                    bill_id=b.id,
                    title=f"📅 Payment Due: {b.name}",
                    message=f"Your {b.category} bill of ₹{b.amount:,.2f} is due in {diff} days. Make sure to complete the payment via {b.payment_method} before the due date to avoid late fees.",
                    category='Bill',
                    priority=priority
                ))
                
    db.session.commit()
