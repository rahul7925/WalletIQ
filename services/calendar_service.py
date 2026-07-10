from datetime import date
import calendar

def get_monthly_calendar_events(user_id: int, year: int, month: int) -> list:
    from app import Bill, User, ist_now
    
    events = []
    user = User.query.get(user_id)
    if not user:
        return []
        
    # 1. Salary Credit Event
    # Standard: Salary expected on 1st of the month
    if user.monthly_income and user.monthly_income > 0:
        events.append({
            'title': '💼 Expected Salary Credit',
            'amount': user.monthly_income,
            'date': f"{year}-{month:02d}-01",
            'type': 'salary',
            'category': 'Salary',
            'priority': 'Low',
            'is_paid': True
        })
        
    # 2. Bill due events
    # For the specified month and year, map due days of active bills
    bills = Bill.query.filter_by(user_id=user_id).all()
    num_days = calendar.monthrange(year, month)[1]
    
    for b in bills:
        # Check if one-time bill has specific date matching this month/year
        if b.due_date:
            if b.due_date.year == year and b.due_date.month == month:
                events.append({
                    'id': b.id,
                    'title': f"🔔 {b.name}",
                    'amount': b.amount,
                    'date': b.due_date.isoformat(),
                    'type': 'bill',
                    'category': b.category,
                    'priority': b.priority,
                    'is_paid': b.is_paid
                })
        else:
            # Recurring bill - map due_day to this year & month
            due_day = min(b.due_day, num_days)  # Avoid out-of-range days
            events.append({
                'id': b.id,
                'title': f"🔔 {b.name}",
                'amount': b.amount,
                'date': f"{year}-{month:02d}-{due_day:02d}",
                'type': 'bill',
                'category': b.category,
                'priority': b.priority,
                'is_paid': b.is_paid
            })
            
    return events
