import os
import json
import math
import random

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'loan_model.json')

class PurePythonLogisticRegression:
    def __init__(self):
        # 9 features: income, expenses, savings, investments, existing_debt, employment_status, credit_score, requested_amount, tenure_months
        self.weights = [0.0] * 9
        self.bias = 0.0

    def sigmoid(self, z):
        # Cap z to avoid overflow errors
        z = max(-50.0, min(50.0, z))
        return 1.0 / (1.0 + math.exp(-z))

    def predict_proba(self, X_row):
        z = self.bias
        for i in range(len(X_row)):
            z += self.weights[i] * X_row[i]
        return self.sigmoid(z)

    def fit(self, X, y, lr=0.1, epochs=250):
        n_samples = len(X)
        for _ in range(epochs):
            for i in range(n_samples):
                p = self.predict_proba(X[i])
                err = y[i] - p
                # Weight update with Gradient Descent
                for j in range(len(self.weights)):
                    self.weights[j] += lr * err * X[i][j]
                self.bias += lr * err

    def save(self, filepath):
        data = {
            'weights': self.weights,
            'bias': self.bias
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)

    def load(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.weights = data['weights']
            self.bias = data['bias']


def train_loan_model():
    """Generates synthetic loan approval training dataset and trains the pure Python Logistic Regression model"""
    random.seed(42)
    n_samples = 1500
    
    X = []
    y = []
    
    for _ in range(n_samples):
        # Raw features
        income = random.uniform(30000, 200000)
        expense_ratio = random.uniform(0.3, 0.9)
        expenses = income * expense_ratio
        savings = income - expenses
        investments = random.uniform(0, 1500000)
        existing_debt = income * random.uniform(0, 0.4)
        employment_status = 1 if random.random() < 0.85 else 0
        credit_score = random.uniform(500, 900)
        requested_amount = random.uniform(100000, 2000000)
        tenure_months = random.choice([12, 24, 36, 60, 120])
        
        # Calculate ground truth decision logic
        interest_mult = 1.0 + 0.10 * (tenure_months / 12.0)
        req_emi = (requested_amount * interest_mult) / tenure_months
        dti = (existing_debt + req_emi) / income
        
        score = 0.0
        if credit_score >= 750:
            score += 0.4
        elif credit_score >= 650:
            score += 0.2
            
        if dti <= 0.35:
            score += 0.4
        elif dti <= 0.45:
            score += 0.2
            
        if (savings / income) >= 0.20:
            score += 0.2
            
        if employment_status == 1:
            score += 0.1
        else:
            score -= 0.35
            
        # Add random noise
        score += random.normalvariate(0, 0.05)
        
        is_eligible = 1 if (score >= 0.5 and credit_score >= 580 and dti <= 0.50 and employment_status == 1) else 0
        
        # Normalize features
        X_row = [
            (income - 30000.0) / 170000.0,
            (expenses - 9000.0) / 171000.0,
            (savings - 0.0) / 140000.0,
            investments / 1500000.0,
            existing_debt / 80000.0,
            float(employment_status),
            (credit_score - 500.0) / 400.0,
            (requested_amount - 100000.0) / 1900000.0,
            (tenure_months - 12.0) / 108.0
        ]
        
        X.append(X_row)
        y.append(is_eligible)
        
    model = PurePythonLogisticRegression()
    model.fit(X, y, lr=0.1, epochs=150)
    
    # Save the model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save(MODEL_PATH)
    return model


def predict_loan_eligibility(user_id: int, requested_amount: float, tenure_months: int, credit_score: int = 700, employment_status: int = 1, lang: str = 'en') -> dict:
    from app import db, User, Expense, Investment, ist_now
    
    model = PurePythonLogisticRegression()
    if not os.path.exists(MODEL_PATH):
        train_loan_model()
    model.load(MODEL_PATH)
            
    user = User.query.get(user_id)
    if not user:
        return {}
        
    income = user.monthly_income or 50000.0
    
    # Current monthly expenses
    now = ist_now()
    this_month_expenses = Expense.query.filter(
        Expense.user_id == user_id,
        db.extract('month', Expense.created_at) == now.month,
        db.extract('year', Expense.created_at) == now.year
    ).all()
    total_expenses = sum(e.amount for e in this_month_expenses)
    if total_expenses <= 0:
        total_expenses = user.monthly_budget or 30000.0
        
    savings = max(0.0, income - total_expenses)
    
    # Investments Portfolio Value
    investments_list = Investment.query.filter_by(user_id=user_id).all()
    portfolio_value = sum(i.current_value for i in investments_list)
    
    # Existing EMI debt
    emi_payments = sum(e.amount for e in this_month_expenses if e.category == 'EMI')
    
    # Normalize input features
    features = [
        (income - 30000.0) / 170000.0,
        (total_expenses - 9000.0) / 171000.0,
        (savings - 0.0) / 140000.0,
        portfolio_value / 1500000.0,
        emi_payments / 80000.0,
        float(employment_status),
        (credit_score - 500.0) / 400.0,
        (requested_amount - 100000.0) / 1900000.0,
        (tenure_months - 12.0) / 108.0
    ]
    
    # Predict eligibility probability
    approval_prob = model.predict_proba(features) * 100.0
    
    # Calculation ratios
    interest_mult = 1.0 + 0.10 * (tenure_months / 12.0)
    requested_emi = (requested_amount * interest_mult) / tenure_months
    
    dti_ratio = ((emi_payments + requested_emi) / income) * 100.0
    
    # Max Eligible Loan Amount Capacity (DTI threshold 45%)
    max_emi_capacity = max(0.0, (income * 0.45) - emi_payments)
    max_loan_amount = (max_emi_capacity * tenure_months) / (1.0 + 0.10 * (tenure_months / 12.0))
    # Round to nearest 10,000
    max_loan_amount = round(max_loan_amount / 10000.0) * 10000.0
    if max_loan_amount < 10000.0:
        max_loan_amount = 0.0
        
    is_eligible = approval_prob >= 50.0 and requested_amount <= max_loan_amount and employment_status == 1
    
    # Risk Assessment
    if credit_score < 650 or dti_ratio > 45.0 or approval_prob < 40.0 or employment_status == 0:
        risk_level = 'High'
    elif credit_score < 720 or dti_ratio > 35.0 or approval_prob < 70.0:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'
        
    # Custom Suggestions
    suggestions = []
    if lang == 'ta':
        if credit_score < 750:
            suggestions.append("மாதாந்திர தவணைகளை முறையாக செலுத்தி உங்கள் கிரெடிட் ஸ்கோரை 750க்கு மேல் உயர்த்துங்கள்.")
        if dti_ratio > 35.0:
            suggestions.append("புதிய கடனைப் பெறுவதற்கு முன் உங்கள் தற்போதைய கடன் சுமையைக் (EMIs) குறைக்கவும்.")
        if (savings / income) < 0.20:
            suggestions.append("சேமிப்பு விகிதத்தை மாதாந்திர வருமானத்தில் 20%க்கு மேல் உயர்த்தவும்.")
        if requested_amount > max_loan_amount and max_loan_amount > 0:
            suggestions.append(f"உங்கள் கடன் தகுதி வரம்பிற்குள் இருக்க கோரப்படும் தொகையை ₹{int(max_loan_amount):,} அல்லது அதற்கும் குறைவாகக் குறைக்கவும்.")
        if len(suggestions) < 3:
            suggestions.append("உங்கள் நிதி சுயவிவரம் நிலையானது. தற்போதைய சேமிப்பு மற்றும் முதலீட்டு முறையைத் தொடரவும்.")
    else:
        if credit_score < 750:
            suggestions.append("Try to improve your credit score above 750 by making timely bill payments.")
        if dti_ratio > 35.0:
            suggestions.append("Reduce your existing monthly EMI obligations to improve repayment capacity.")
        if (savings / income) < 0.20:
            suggestions.append("Increase your monthly savings to at least 20% of your income.")
        if requested_amount > max_loan_amount and max_loan_amount > 0:
            suggestions.append(f"Your requested loan exceeds your maximum limit. Consider reducing it below ₹{int(max_loan_amount):,}.")
        if len(suggestions) < 3:
            suggestions.append("Your financial profile is strong. Maintain this track to ensure quick loan approvals.")
            
    return {
        'is_eligible': bool(is_eligible),
        'approval_probability': round(approval_prob, 2),
        'eligible_amount': round(max_loan_amount, 2),
        'estimated_emi': round(requested_emi, 2),
        'debt_to_income': round(dti_ratio, 2),
        'risk_level': risk_level,
        'suggestions': suggestions[:3],
        'credit_score': credit_score,
        'employment_status': employment_status,
        'requested_amount': requested_amount,
        'tenure_months': tenure_months
    }
