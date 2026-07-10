"""
WalletIQ - ML Category Classifier
Naive Bayes text classifier trained on small curated Indian transaction examples.

Fixes:
- train_model.py had syntax errors (unterminated strings / missing commas / stray
  strings outside of the tuples). This version keeps the same overall intent
  while guaranteeing valid Python syntax.
"""

import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score


# ── Training Data (India-specific) ─────────────────────────────────────────────
# List of (sample_text, label)
data = [
    # Food
    ("Pizza", "Food"), ("Burger", "Food"), ("KFC", "Food"), ("Swiggy", "Food"),
    ("Zomato", "Food"), ("Biryani", "Food"), ("Dosa", "Food"), ("Idli", "Food"),
    ("Coffee", "Food"), ("Tea", "Food"), ("Grocery", "Food"), ("Milk", "Food"),
    ("Dominos", "Food"), ("Lunch", "Food"), ("Dinner", "Food"), ("Breakfast", "Food"),

    # Travel
    ("Cab Fare", "Travel"), ("Taxi Fare", "Travel"), ("Auto Fare", "Travel"),
    ("Uber", "Travel"), ("Ola", "Travel"), ("Bus Ticket", "Travel"),
    ("Train Ticket", "Travel"), ("Flight Booking", "Travel"), ("Toll Plaza", "Travel"),
    ("FASTag Recharge", "Travel"), ("Parking", "Travel"), ("Metro", "Travel"),

    # Entertainment
    ("Netflix", "Entertainment"), ("Amazon Prime", "Entertainment"), ("Hotstar", "Entertainment"),
    ("YouTube Premium", "Entertainment"), ("Spotify", "Entertainment"),
    ("Movie Ticket", "Entertainment"), ("Cinema Ticket", "Entertainment"),
    ("PVR", "Entertainment"), ("INOX", "Entertainment"), ("BookMyShow", "Entertainment"),

    # Bills
    ("Electricity Payment", "Bills"), ("Water Charges", "Bills"), ("Broadband Bill", "Bills"),
    ("Mobile Bill", "Bills"), ("Rent", "Bills"), ("Insurance Premium", "Bills"),
    ("DTH Recharge", "Bills"), ("Gas Cylinder", "Bills"), ("EMI", "Bills"),
    ("Subscription", "Bills"), ("Internet", "Bills"),

    # Shopping
    ("Amazon", "Shopping"), ("Flipkart", "Shopping"), ("Myntra", "Shopping"),
    ("Electronics", "Shopping"), ("Shoes", "Shopping"), ("Jeans", "Shopping"),
    ("Mobile Phone", "Shopping"), ("Laptop", "Shopping"),

    # Health
    ("Apollo Hospital", "Health"), ("Fortis Hospital", "Health"), ("Pharmacy Purchase", "Health"),
    ("Doctor Fee", "Health"), ("Gym Membership", "Health"), ("Medicine", "Health"),
    ("Lab Charges", "Health"), ("Health Insurance Premium", "Health"),

    # Education
    ("College Fees", "Education"), ("Tuition", "Education"), ("Exam Fee", "Education"),
    ("Online Class", "Education"), ("AWS Course", "Education"), ("Azure Course", "Education"),
    ("Books", "Education"), ("Stationery", "Education"),

    # Savings/Investment
    ("Mutual Fund SIP", "Savings"), ("PPF Deposit", "Savings"), ("NPS Contribution", "Savings"),
    ("Fixed Deposit Opening", "Savings"), ("Gold ETF", "Savings"), ("Index Fund", "Savings"),
    ("SIP Installment", "Savings"), ("Stock Investment", "Savings"), ("ETF Investment", "Savings"),

    # Cash Withdrawal (kept to avoid classifier collapse)
    ("ATM Withdrawal", "Cash Withdrawal"), ("Cash Withdrawal", "Cash Withdrawal"),
    ("Bank Withdrawal", "Cash Withdrawal"),

    # Salary
    ("Salary Credit", "Salary"), ("Paycheck", "Salary"), ("Income", "Salary"),
    ("Bonus", "Salary"), ("Rental Income", "Salary"), ("Dividends", "Salary"),

    # Transfer
    ("UPI Transfer", "Transfer"), ("NEFT Transfer", "Transfer"), ("IMPS Transfer", "Transfer"),
    ("Bank Transfer", "Transfer"), ("Fund Transfer", "Transfer"), ("Money Sent", "Transfer"),
]


# Ensure data is a list of tuples
if not all(isinstance(t, tuple) and len(t) == 2 for t in data):
    raise ValueError("Training data must be a list of (text, label) tuples")

titles, categories = zip(*data)


# ── Model Pipeline ────────────────────────────────────────────────────────────
pipeline = Pipeline(
    [
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=2000,
                lowercase=True,
            ),
        ),
        ("clf", MultinomialNB(alpha=0.5)),
    ]
)


# ── Train / Evaluate ──────────────────────────────────────────────────────────
# NOTE: With small datasets, stratified split can fail if any class has <2 samples.
# So we fall back to a non-stratified split when needed.
try:
    X_train, X_test, y_train, y_test = train_test_split(
        titles,
        categories,
        test_size=0.15,
        random_state=42,
        stratify=categories,
    )
except ValueError:
    X_train, X_test, y_train, y_test = train_test_split(
        titles,
        categories,
        test_size=0.15,
        random_state=42,
    )

pipeline.fit(X_train, y_train)

# Evaluate
if len(set(y_test)) > 0:
    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy:.1%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))


# ── Save Model ────────────────────────────────────────────────────────────────
# Save split for legacy compatibility + full pipeline
pickle.dump(pipeline.named_steps["clf"], open("model.pkl", "wb"))
pickle.dump(pipeline.named_steps["tfidf"], open("vectorizer.pkl", "wb"))
pickle.dump(pipeline, open("pipeline.pkl", "wb"))

print("model.pkl, vectorizer.pkl, pipeline.pkl saved successfully!")


# ── Quick Test ────────────────────────────────────────────────────────────────
test_cases = [
    "Swiggy order",
    "Uber cab",
    "Netflix subscription",
    "Jio recharge",
    "Amazon shopping",
    "Gym membership",
]

print("\nSample Predictions:")
for t in test_cases:
    pred = pipeline.predict([t])[0]
    print(f"  '{t}' -> {pred}")

