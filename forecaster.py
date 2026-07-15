import logging
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from app import db, User, Expense, Investment, ist_now

log = logging.getLogger('walletiq.forecaster')

def run_financial_projection(user_id: int, horizon_months: int = 12, salary_growth_pct: float = 5.0, inflation_pct: float = 6.0, method: str = 'formula') -> dict:
    """
    Run a multi-scenario monthly financial projection for a user.
    Method can be 'formula' or 'ml' (which uses Scikit-Learn Linear Regression on historical expenses).
    """
    user = db.session.get(User, user_id)
    if not user:
        return {}

    now = ist_now()

    # 1. Gather baseline stats
    base_income = max(0.0, user.monthly_income)
    base_emergency = max(0.0, user.emergency_savings)
    base_budget = max(0.0, user.monthly_budget)

    # Fetch total current value of investments
    investments = Investment.query.filter_by(user_id=user_id).all()
    base_investments = sum(i.current_value for i in investments)

    # Fetch current month expenses
    expenses = Expense.query.filter_by(user_id=user_id).all()
    this_month_expenses = [e for e in expenses 
                           if e.created_at.month == now.month 
                           and e.created_at.year == now.year]
    current_expenses = sum(e.amount for e in this_month_expenses)

    # Fallback if no expenses this month
    if current_expenses <= 0:
        current_expenses = base_budget if base_budget > 0 else 20000.0

    # 2. Compile historical expense data for ML option
    historical_exp_vals = []
    has_ml_history = False
    lr_model = None

    if method == 'ml':
        # Group expenses by calendar month
        monthly_totals = defaultdict(float)
        for e in expenses:
            key = (e.created_at.year, e.created_at.month)
            monthly_totals[key] += e.amount

        # Sort keys chronologically
        sorted_keys = sorted(monthly_totals.keys())
        historical_exp_vals = [monthly_totals[k] for k in sorted_keys]

        if len(historical_exp_vals) >= 3:
            try:
                from sklearn.linear_model import LinearRegression
                import numpy as np

                # X is the chronological month index: [[0], [1], [2], ...]
                X = np.array(list(range(len(historical_exp_vals)))).reshape(-1, 1)
                y = np.array(historical_exp_vals)
                
                lr_model = LinearRegression()
                lr_model.fit(X, y)
                has_ml_history = True
                log.info(f"Fitted linear regression model on {len(historical_exp_vals)} months of expense data for user {user_id}")
            except Exception as e:
                log.error(f"Failed to fit Linear Regression model for user {user_id}: {e}. Falling back to formula.")

    # 3. Projection lists structure
    months_labels = []
    # Project dates
    for m in range(1, horizon_months + 1):
        future_date = now + relativedelta(months=m)
        months_labels.append(future_date.strftime('%b %Y'))

    # Define return structure
    results = {
        'months': months_labels,
        'scenarios': {
            'conservative': {
                'monthly_income': [], 'monthly_expenses': [], 'monthly_savings': [],
                'net_cash_flow': [], 'net_worth': [], 'final_net_worth': 0.0, 'final_savings': 0.0
            },
            'moderate': {
                'monthly_income': [], 'monthly_expenses': [], 'monthly_savings': [],
                'net_cash_flow': [], 'net_worth': [], 'final_net_worth': 0.0, 'final_savings': 0.0
            },
            'aggressive': {
                'monthly_income': [], 'monthly_expenses': [], 'monthly_savings': [],
                'net_cash_flow': [], 'net_worth': [], 'final_net_worth': 0.0, 'final_savings': 0.0
            }
        },
        'method_used': 'ml' if has_ml_history else 'formula',
        'historical_points_count': len(historical_exp_vals)
    }

    # Scenario parameters setup
    # Format: (growth_adj, inflation_adj, r_annual, savings_efficiency)
    scenarios_config = {
        'conservative': (-1.5, 1.0, 0.06, 0.85),
        'moderate': (0.0, 0.0, 0.12, 1.0),
        'aggressive': (1.5, -1.0, 0.15, 1.15)
    }

    for name, (g_adj, i_adj, r_ann, sav_eff) in scenarios_config.items():
        # Yearly compounding adjustments
        g_rate = max(0.0, (salary_growth_pct + g_adj) / 100.0)
        i_rate = max(0.0, (inflation_pct + i_adj) / 100.0)
        r_monthly = r_ann / 12.0

        # State trackers for this scenario
        cash_savings = base_emergency
        invested_wealth = base_investments
        accumulated_savings = 0.0

        for t in range(1, horizon_months + 1):
            year_idx = (t - 1) // 12

            # Income projection
            proj_income = base_income * ((1 + g_rate) ** year_idx)

            # Expense projection
            if has_ml_history and lr_model:
                # Predict expense using Linear Regression
                next_idx = len(historical_exp_vals) - 1 + t
                pred_exp_base = lr_model.predict([[next_idx]])[0]
                # Bounding between ₹2,000 and 2.5 * base_income to prevent wild models
                pred_exp_base = max(2000.0, min(pred_exp_base, base_income * 2.5))
                # Apply inflation growth
                proj_expenses = pred_exp_base * ((1 + i_rate) ** year_idx)
            else:
                # Formula-based inflation growth
                proj_expenses = current_expenses * ((1 + i_rate) ** year_idx)

            # Cash Flow Calculations
            # S_t = max(0, income - expenses) * efficiency
            net_cash_flow = proj_income - proj_expenses
            proj_savings = max(0.0, net_cash_flow * sav_eff)
            accumulated_savings += proj_savings

            # Asset growth compounding
            # We divide monthly savings between emergency cash and investments
            # Cash gets 15% of savings until it reaches a buffer of 6 months of expenses, then 100% goes to investments
            if cash_savings < (proj_expenses * 6.0):
                cash_portion = proj_savings * 0.15
                inv_portion = proj_savings * 0.85
            else:
                cash_portion = proj_savings * 0.05 # small trickle to cash
                inv_portion = proj_savings * 0.95

            # Growth
            cash_savings += cash_portion
            invested_wealth = (invested_wealth + inv_portion) * (1 + r_monthly)

            net_worth = cash_savings + invested_wealth

            # Append to lists
            results['scenarios'][name]['monthly_income'].append(round(proj_income, 2))
            results['scenarios'][name]['monthly_expenses'].append(round(proj_expenses, 2))
            results['scenarios'][name]['monthly_savings'].append(round(proj_savings, 2))
            results['scenarios'][name]['net_cash_flow'].append(round(net_cash_flow, 2))
            results['scenarios'][name]['net_worth'].append(round(net_worth, 2))

        # Store final outputs
        results['scenarios'][name]['final_net_worth'] = round(net_worth, 2)
        results['scenarios'][name]['final_savings'] = round(accumulated_savings, 2)

    return results
