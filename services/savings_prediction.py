def compute_savings_prediction(user_id: int, salary_growth: float = 8.0, inflation: float = 6.0, moderate_return: float = 10.0) -> dict:
    from app import db, User, Expense, Investment, ist_now

    user = User.query.get(user_id)
    if not user:
        return {}

    income = user.monthly_income or 50000.0
    
    # Get current monthly expenses
    now = ist_now()
    this_month_expenses = Expense.query.filter(
        Expense.user_id == user_id,
        db.extract('month', Expense.created_at) == now.month,
        db.extract('year', Expense.created_at) == now.year
    ).all()
    total_expenses = sum(e.amount for e in this_month_expenses)
    if total_expenses <= 0:
        total_expenses = user.monthly_budget or 30000.0

    # Current Investments Portfolio
    investments_list = Investment.query.filter_by(user_id=user_id).all()
    portfolio_value = sum(i.current_value for i in investments_list)

    # Current Monthly Investments
    savings_expenses = sum(e.amount for e in this_month_expenses if e.category == 'Savings')
    this_month_investments = [i for i in investments_list
                              if i.created_at.month == now.month
                              and i.created_at.year == now.year]
    new_investments = sum(i.invested for i in this_month_investments)
    monthly_invested = savings_expenses + new_investments
    
    # Calculate investment ratio
    if income > 0:
        investment_ratio = monthly_invested / income
    else:
        investment_ratio = 0.15  # Default 15%
    if investment_ratio > 0.8:
        investment_ratio = 0.8  # Cap at 80% to be realistic

    # Helper function to run a simulation for a scenario
    def run_simulation(r_annual, sal_growth_annual, infl_annual, exp_mult):
        months = list(range(61)) # 0 to 60 months
        net_worth = [portfolio_value]
        income_proj = [income]
        expenses_proj = [total_expenses * exp_mult]
        savings_proj = [income - expenses_proj[0]]
        portfolio = [portfolio_value]
        cash = [0.0]

        r_monthly = (1.0 + r_annual) ** (1.0/12.0) - 1.0
        sal_growth_monthly = sal_growth_annual
        infl_monthly = infl_annual

        for t in range(1, 61):
            year_idx = (t - 1) // 12
            inc = income * ((1.0 + sal_growth_monthly) ** year_idx)
            exp = (total_expenses * exp_mult) * ((1.0 + infl_monthly) ** year_idx)
            sav = inc - exp
            sip = max(0.0, sav * investment_ratio)
            
            p_val = portfolio[t-1] * (1.0 + r_monthly) + sip
            c_val = cash[t-1] + (sav - sip)
            
            portfolio.append(p_val)
            cash.append(c_val)
            net_worth.append(p_val + c_val)
            income_proj.append(inc)
            expenses_proj.append(exp)
            savings_proj.append(sav)

        # Round all values for clean JSON and charting
        return {
            'months': months,
            'net_worth': [round(x, 2) for x in net_worth],
            'income': [round(x, 2) for x in income_proj],
            'expenses': [round(x, 2) for x in expenses_proj],
            'savings': [round(x, 2) for x in savings_proj],
            'savings_3m': round(net_worth[3], 2),
            'savings_6m': round(net_worth[6], 2),
            'savings_1y': round(net_worth[12], 2),
            'savings_5y': round(net_worth[60], 2),
        }

    # Moderate Scenario (Expected Case)
    moderate = run_simulation(
        r_annual=moderate_return / 100.0,
        sal_growth_annual=salary_growth / 100.0,
        infl_annual=inflation / 100.0,
        exp_mult=1.0
    )

    # Conservative Scenario (Worst Case)
    conservative = run_simulation(
        r_annual=6.0 / 100.0,
        sal_growth_annual=max(0.0, salary_growth - 2.0) / 100.0,
        infl_annual=(inflation + 1.0) / 100.0,
        exp_mult=1.10  # 10% higher expenses
    )

    # Aggressive Scenario (Best Case)
    aggressive = run_simulation(
        r_annual=(moderate_return + 5.0) / 100.0,
        sal_growth_annual=(salary_growth + 2.0) / 100.0,
        infl_annual=max(0.0, inflation - 1.0) / 100.0,
        exp_mult=0.85  # 15% expense reduction
    )

    return {
        'conservative': conservative,
        'moderate': moderate,
        'aggressive': aggressive,
        'current_savings': round(portfolio_value, 2),
        'salary_growth': salary_growth,
        'inflation': inflation,
        'moderate_return': moderate_return
    }
