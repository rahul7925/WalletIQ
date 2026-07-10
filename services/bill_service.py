from datetime import date
from app import db

def get_user_bills(user_id: int) -> list:
    from app import Bill
    return Bill.query.filter_by(user_id=user_id).order_by(Bill.due_date.asc(), Bill.due_day.asc()).all()

def create_bill(user_id: int, name: str, amount: float, category: str, due_day: int,
                is_recurring: bool = True, due_date_str: str = None, priority: str = 'Medium',
                auto_pay: bool = False, payment_method: str = 'UPI', note: str = '') -> dict:
    from app import Bill, ist_now
    
    due_date = None
    if due_date_str:
        try:
            due_date = date.fromisoformat(due_date_str)
        except ValueError:
            pass

    bill = Bill(
        user_id=user_id,
        name=name,
        amount=round(amount, 2),
        category=category,
        due_day=due_day,
        is_recurring=is_recurring,
        due_date=due_date,
        priority=priority,
        auto_pay=auto_pay,
        payment_method=payment_method,
        note=note,
        is_paid=False
    )
    db.session.add(bill)
    db.session.commit()
    
    return {
        'id': bill.id,
        'name': bill.name,
        'amount': bill.amount,
        'category': bill.category,
        'priority': bill.priority,
        'auto_pay': bill.auto_pay,
        'is_paid': bill.is_paid
    }

def update_bill(user_id: int, bill_id: int, name: str, amount: float, category: str, due_day: int,
                is_recurring: bool = True, due_date_str: str = None, priority: str = 'Medium',
                auto_pay: bool = False, payment_method: str = 'UPI', note: str = '', is_paid: bool = False) -> dict:
    from app import Bill
    bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()
    if not bill:
        return {}

    due_date = None
    if due_date_str:
        try:
            due_date = date.fromisoformat(due_date_str)
        except ValueError:
            pass

    bill.name = name
    bill.amount = round(amount, 2)
    bill.category = category
    bill.due_day = due_day
    bill.is_recurring = is_recurring
    bill.due_date = due_date
    bill.priority = priority
    bill.auto_pay = auto_pay
    bill.payment_method = payment_method
    bill.note = note
    bill.is_paid = is_paid
    
    if not is_paid:
        bill.paid_date = None

    db.session.commit()
    return {
        'id': bill.id,
        'name': bill.name,
        'amount': bill.amount,
        'category': bill.category,
        'is_paid': bill.is_paid
    }

def delete_bill(user_id: int, bill_id: int) -> bool:
    from app import Bill
    bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()
    if not bill:
        return False
    db.session.delete(bill)
    db.session.commit()
    return True

def auto_generate_recurring_bills(user_id: int):
    """Checks recurring bills and marks them as unpaid at the start of a new month if they were paid last month"""
    from app import Bill, ist_now
    now = ist_now()
    bills = Bill.query.filter_by(user_id=user_id, is_recurring=True, is_paid=True).all()
    
    for b in bills:
        if b.paid_date and b.paid_date.month != now.month:
            # Re-generate reminder for the current month
            b.is_paid = False
            b.paid_date = None
            
    db.session.commit()
