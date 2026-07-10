def compute_financial_health(user_id: int) -> dict:
    from app import db, User, Expense, Budget, Investment, Bill, ist_now

    now = ist_now()
    user = User.query.get(user_id)
    if not user:
        return {}

    income = user.monthly_income or 50000.0
    if income <= 0:
        income = 1.0  # Avoid division by zero

    # 1. Monthly Expenses
    expenses_list = Expense.query.filter_by(user_id=user_id).all()
    this_month_expenses = [e for e in expenses_list
                           if e.created_at.month == now.month
                           and e.created_at.year == now.year]
    total_expenses = sum(e.amount for e in this_month_expenses)

    # 2. Savings Rate (30% weight)
    # Savings = Income - Expenses
    savings = income - total_expenses
    savings_rate = (savings / income) * 100
    if savings_rate >= 40:
        savings_score = 100
    elif savings_rate >= 20:
        savings_score = 80 + (savings_rate - 20) * 1.0
    elif savings_rate >= 0:
        savings_score = savings_rate * 4.0
    else:
        savings_score = 0

    # 3. Expense Control (20% weight)
    # Target: Expenses <= 50% of income
    expense_ratio = (total_expenses / income) * 100
    if expense_ratio <= 50:
        expense_score = 100
    elif expense_ratio >= 100:
        expense_score = 0
    else:
        expense_score = 100 - (expense_ratio - 50) * 2.0

    # 4. Investment Ratio (20% weight)
    savings_expenses = sum(e.amount for e in this_month_expenses if e.category == 'Savings')
    investments_list = Investment.query.filter_by(user_id=user_id).all()
    this_month_investments = [i for i in investments_list
                              if i.created_at.month == now.month
                              and i.created_at.year == now.year]
    new_investments = sum(i.invested for i in this_month_investments)
    total_invested = savings_expenses + new_investments
    
    investment_ratio = (total_invested / income) * 100
    if investment_ratio >= 20:
        investment_score = 100
    elif investment_ratio >= 10:
        investment_score = 60 + (investment_ratio - 10) * 4.0
    elif investment_ratio >= 0:
        investment_score = investment_ratio * 6.0
    else:
        investment_score = 0

    # 5. Budget Adherence (15% weight)
    # Fetch budgets for this month
    budgets = Budget.query.filter_by(
        user_id=user_id,
        month=now.month,
        year=now.year
    ).all()
    
    # Calculate spending by category
    cat_totals = {}
    for e in this_month_expenses:
        if e.category != 'Savings':
            cat_totals[e.category] = cat_totals.get(e.category, 0.0) + e.amount
            
    budget_score = 100.0
    if budgets:
        over_budget_count = 0
        total_overspent = 0.0
        for b in budgets:
            spent = cat_totals.get(b.category, 0.0)
            if spent > b.amount:
                over_budget_count += 1
                total_overspent += (spent - b.amount)
        # Calculate score based on overspent budget categories
        budget_score = max(0.0, 100.0 - (over_budget_count * 25.0) - (total_overspent / 1000.0))
    else:
        # Default average budget adherence score if no budgets set
        budget_score = 75.0

    # 6. Emergency Fund (10% weight)
    # Target: Portfolio Current Value covers >= 6 months of expenses
    portfolio_value = sum(i.current_value for i in investments_list)
    # Monthly expenses (if 0, default to income / 2 or 15000 to be safe)
    ref_expenses = total_expenses if total_expenses > 0 else (income * 0.5)
    months_covered = portfolio_value / ref_expenses
    if months_covered >= 6:
        emergency_score = 100
    else:
        emergency_score = (months_covered / 6.0) * 100

    # 7. Debt Ratio (5% weight)
    # EMI Expenses for this month
    emi_payments = sum(e.amount for e in this_month_expenses if e.category == 'EMI')
    debt_ratio = (emi_payments / income) * 100
    if debt_ratio <= 10:
        debt_score = 100
    elif debt_ratio >= 50:
        debt_score = 0
    else:
        debt_score = 100 - (debt_ratio - 10) * 2.5

    # Weighted Score calculation
    final_score = (
        savings_score * 0.30 +
        expense_score * 0.20 +
        investment_score * 0.20 +
        budget_score * 0.15 +
        emergency_score * 0.10 +
        debt_score * 0.05
    )

    # Health status assignment
    score_int = int(round(final_score))
    if score_int >= 85:
        status = 'Excellent'
    elif score_int >= 70:
        status = 'Good'
    elif score_int >= 50:
        status = 'Average'
    elif score_int >= 35:
        status = 'Needs Improvement'
    else:
        status = 'Critical'

    # Get overdue/due bills
    from datetime import date
    bills = Bill.query.filter_by(user_id=user_id).all()
    overdue = [b for b in bills if not b.is_paid and b.due_day < now.day]
    due_soon = [b for b in bills if not b.is_paid and now.day <= b.due_day <= now.day + 5]

    return {
        "score": score_int,
        "status": status,
        "savings_rate": round(savings_rate, 2),
        "savings_score": round(savings_score, 1),
        "expense_ratio": round(expense_ratio, 2),
        "expense_score": round(expense_score, 1),
        "investment_ratio": round(investment_ratio, 2),
        "investment_score": round(investment_score, 1),
        "budget_score": round(budget_score, 1),
        "emergency_fund_score": round(emergency_score, 1),
        "months_covered": round(months_covered, 2),
        "debt_ratio": round(debt_ratio, 2),
        "debt_score": round(debt_score, 1),
        "income": income,
        "expenses": total_expenses,
        "savings": savings,
        "portfolio_value": portfolio_value,
        "new_investments": new_investments,
        "savings_expenses": savings_expenses,
        "emi_payments": emi_payments,
        "overdue_bills": len(overdue),
        "due_soon_bills": len(due_soon),
        "top_category": max(cat_totals, key=cat_totals.get) if cat_totals else '—',
    }
