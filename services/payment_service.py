from app import db

def pay_bill_service(user_id: int, bill_id: int, payment_mode: str = 'UPI') -> dict:
    from app import Bill, Expense, PaymentHistory, Notification, ist_now
    
    # Check if bill exists and belongs to the user
    bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()
    if not bill:
        return {'success': False, 'error': 'Bill not found'}
        
    if bill.is_paid:
        return {'success': False, 'error': 'Bill is already paid'}
        
    now = ist_now()
    
    # 1. Update Bill status
    bill.is_paid = True
    bill.paid_date = now.date()
    
    # 2. Add to PaymentHistory
    payment = PaymentHistory(
        user_id=user_id,
        bill_id=bill.id,
        name=bill.name,
        amount=bill.amount,
        paid_date=now.date(),
        payment_mode=payment_mode
    )
    db.session.add(payment)
    
    # 3. Add to Expense table (Synchronized tracking)
    # Check if bill category maps to a valid expense category
    valid_categories = ['Food', 'Travel', 'Entertainment', 'Bills', 'Shopping', 'Health', 'Education', 'Savings', 'EMI', 'Other']
    expense_cat = bill.category
    if expense_cat not in valid_categories:
        # Fallbacks
        if expense_cat in ['Netflix', 'Spotify', 'Amazon Prime', 'ChatGPT Plus']:
            expense_cat = 'Entertainment'
        elif expense_cat in ['Home Loan', 'Car Loan', 'Personal Loan', 'Education Loan']:
            expense_cat = 'EMI'
        elif expense_cat in ['SIP', 'Mutual Funds', 'Fixed Deposit', 'Recurring Deposit']:
            expense_cat = 'Savings'
        else:
            expense_cat = 'Bills'
            
    expense = Expense(
        user_id=user_id,
        title=f"Paid: {bill.name}",
        amount=bill.amount,
        category=expense_cat,
        payment_mode=payment_mode,
        created_at=now  # Sync time
    )
    db.session.add(expense)
    
    # 4. Resolve/Read any active notifications for this bill
    notifications = Notification.query.filter_by(user_id=user_id, bill_id=bill.id, is_read=False).all()
    for n in notifications:
        n.is_read = True
        
    db.session.commit()
    
    return {
        'success': True,
        'message': f"Successfully paid {bill.name}!",
        'payment_id': payment.id,
        'expense_id': expense.id
    }

def get_user_payment_history(user_id: int) -> list:
    from app import PaymentHistory
    return PaymentHistory.query.filter_by(user_id=user_id).order_by(PaymentHistory.paid_date.desc()).limit(15).all()
