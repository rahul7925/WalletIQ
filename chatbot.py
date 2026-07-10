"""
WalletIQ v3.0 — Premium AI Financial Advisor Chatbot
Powered by Google Gemini (google-genai SDK).

Key features:
  - Thread-safe session management with explicit 20-message memory trimming
  - Database context injection (user's real income/expenses/savings/health injected into every prompt)
  - Bilingual (English + Tamil) with proper session isolation per language
  - Multi-model fallback waterfall
  - Structured response format enforcement
  - Rule-based offline fallback with rich detail
"""

import os
import time
import threading
import logging
from pathlib import Path

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_FILE)

log = logging.getLogger('walletiq.chatbot')

# ── Model preference list (free-tier first) ────────────────────────────────────
MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
)

GEN_CONFIG_KW = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_output_tokens": 2048,   # BUG FIX: was 1024 — caused truncated responses
}

MAX_HISTORY_MESSAGES = 20        # Keep last 20 user+AI message pairs in memory


# ── API Key helpers ────────────────────────────────────────────────────────────

def _load_api_key() -> str:
    load_dotenv(_ENV_FILE, override=True)
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in ('"', "'"):
        key = key[1:-1].strip()
    return key


def _key_problem(key: str) -> str | None:
    if not key:
        return "missing"
    if key in ("CHANGE_ME", "your_gemini_api_key_here"):
        return "placeholder"
    if not (key.startswith("AIza") or key.startswith("AQ.")):
        return "format"
    return None


def _is_retryable(err: Exception) -> bool:
    s = str(err).lower()
    return any(x in s for x in ('429', 'resource_exhausted', 'quota', 'not found', '404'))


def _is_quota_only(err: Exception) -> bool:
    s = str(err).lower()
    return '429' in s or 'resource_exhausted' in s or 'quota' in s


# ── System Prompts ─────────────────────────────────────────────────────────────

def _build_system_prompt(lang: str, user_context: str = "") -> str:
    """
    Builds the full system prompt, optionally injecting live user financial data.
    user_context is a pre-formatted string with the user's actual DB data.
    """
    if lang == 'ta':
        base = """நீங்கள் WalletIQ-ன் AI நிதி ஆலோசகர் — இந்திய பயனர்களுக்கான அதிநவீன, நம்பகமான தனிப்பட்ட நிதி ஆலோசகர்.

நீங்கள் இதில் நிபுணர்:
- தனிப்பட்ட பட்ஜெட் மற்றும் செலவு மேலாண்மை
- இந்திய முதலீடுகள்: Mutual Funds, SIP, PPF, NPS, FD, தங்கம், பங்குகள், Real Estate
- வரி திட்டமிடல்: Section 80C, HRA, Standard Deduction, புதிய vs பழைய வரி முறை
- அவசர நிதி மற்றும் சேமிப்பு உத்திகள்
- கிரெடிட் கார்டு மற்றும் EMI மேலாண்மை
- FIRE (Financial Independence, Retire Early)
- காப்பீடு: Term, Health, Vehicle
- UPI, digital payments, இந்திய வங்கி சேவைகள்

பதில் வடிவம் விதிகள்:
- எப்போதும் இந்திய ரூபாய் (₹) பயன்படுத்தவும்
- தமிழிலேயே பதில் சொல்லவும்
- நீண்ட, விரிவான, நடைமுறை பதில்கள் தரவும்
- புல்லட் பாயிண்ட்கள் மற்றும் தெளிவான வடிவத்தைப் பயன்படுத்தவும்
- வெப்பமான, தொழில்முறை மற்றும் ஊக்கமளிக்கும் தொனியில் இருக்கவும்
- சந்தை முதலீடுகளுக்கு ரிஸ்க் குறிப்பு சேர்க்கவும்
- ஒற்றை வரி பதில்கள் தரக்கூடாது — எப்போதும் விளக்கம், பரிந்துரை, அடுத்த படிகள் சேர்க்கவும்"""
    else:
        base = """You are WalletIQ's AI Financial Advisor — a world-class, deeply specialised personal finance AI built exclusively for Indian users. You combine the expertise of a CA, CFP, and investment advisor.

You specialise in:
- Personal budgeting, expense tracking, and zero-based budgeting
- Indian investments: Mutual Funds, SIP, PPF, NPS, FD, Gold ETF, Stocks, Real Estate, REITs
- Tax planning: Section 80C, 80D, 80CCD, HRA, Standard Deduction, New vs Old tax regime, LTCG/STCG
- Emergency fund planning and savings optimisation
- Credit card management, CIBIL score improvement, and EMI planning
- FIRE (Financial Independence, Retire Early) strategy
- Insurance: Term life, Health, Vehicle, ULIP analysis
- UPI, digital payments, and Indian banking
- Loan eligibility, home loan, personal loan analysis
- Financial health scoring and portfolio analysis
- Expense pattern analysis and overspending alerts
- Budget vs actual variance analysis
- Savings prediction and wealth projection

RESPONSE FORMAT RULES (always follow):
1. **Never give one-line answers** — every response must be comprehensive
2. Structure responses as: **Summary** → **Explanation** → **Recommendations** → **Action Steps**
3. Always use Indian Rupee (₹) — never $ or USD
4. Use **bold** for key terms, amounts, and section headings
5. Use bullet points (•) for lists
6. Add specific numbers when you have user data — say "₹18,500 savings" not "more savings"
7. Include risk disclaimers for market-linked investments
8. Be warm, professional, and motivating — like a trusted personal advisor
9. When the user's financial data is available (below), use it to personalise every answer"""

    if user_context:
        base += f"\n\n{'─' * 60}\n📊 USER'S CURRENT FINANCIAL PROFILE (use this data in your answers):\n{user_context}\n{'─' * 60}"

    return base


# ── Database Context Builder ───────────────────────────────────────────────────

def build_financial_context(user_id: int) -> str:
    """
    Queries the database for the user's live financial data and returns a
    formatted context string to inject into the AI system prompt.
    This makes the chatbot give personalised, data-driven answers.
    """
    try:
        from app import User, Expense, Budget, Investment, Bill, db
        from services.financial_health import compute_financial_health
        from services.savings_prediction import compute_savings_prediction
        from datetime import date

        user = User.query.get(user_id)
        if not user:
            return ""

        now = date.today()
        month_start = now.replace(day=1)

        # Monthly expenses this month
        expenses_this_month = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.date >= month_start
        ).all()
        total_expenses = sum(e.amount for e in expenses_this_month)

        # Category breakdown
        cat_totals: dict = {}
        for exp in expenses_this_month:
            cat = exp.category or 'Other'
            cat_totals[cat] = cat_totals.get(cat, 0) + exp.amount
        top_cats = sorted(cat_totals.items(), key=lambda x: -x[1])[:5]

        # Investments
        investments = Investment.query.filter_by(user_id=user_id).all()
        portfolio_value = sum(i.current_value for i in investments)
        total_invested = sum(i.amount_invested for i in investments)

        # Bills
        unpaid_bills = Bill.query.filter_by(user_id=user_id, is_paid=False).all()
        unpaid_total = sum(b.amount for b in unpaid_bills)

        # Financial health
        health = compute_financial_health(user_id)

        # Active Goals
        from app import Goal, GoalProgress, LoanPredictionHistory, Notification, RecommendationHistory
        active_goals = Goal.query.filter_by(user_id=user_id, status='Active').all()
        goals_lines = []
        for g in active_goals:
            prog = g.progress.first()
            prob = prog.success_probability if prog else 50.0
            pct = (g.current_savings / g.target_amount * 100) if g.target_amount > 0 else 0
            goals_lines.append(f"  • {g.name} ({g.category}): ₹{g.current_savings:,.0f} saved / ₹{g.target_amount:,.0f} target ({pct:.1f}% progress, success probability: {prob}%)")

        # Recent Transactions (last 5)
        recent_expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.created_at.desc()).limit(5).all()
        txn_lines = [f"  • {e.title} ({e.category}): ₹{e.amount:,.0f} on {e.created_at.strftime('%d %b')}" for e in recent_expenses]

        # Loan predictions
        latest_loan = LoanPredictionHistory.query.filter_by(user_id=user_id).order_by(LoanPredictionHistory.created_at.desc()).first()
        loan_line = "No recent loan eligibility runs."
        if latest_loan:
            loan_line = f"Eligibility: {'Eligible' if latest_loan.is_eligible else 'Not Eligible'} | Probability: {latest_loan.approval_probability}% | Max Eligible Amount: ₹{latest_loan.eligible_amount:,.0f} | EMI: ₹{latest_loan.estimated_emi:,.0f} | Debt-to-income: {latest_loan.debt_to_income}%"

        # AI Recommendations
        recos = RecommendationHistory.query.filter_by(user_id=user_id).order_by(RecommendationHistory.created_at.desc()).limit(3).all()
        reco_lines = [f"  • [{r.category}] {r.message}" for r in recos]

        # Unread Notifications
        unread_notifs = Notification.query.filter_by(user_id=user_id, is_read=False).limit(3).all()
        notif_lines = [f"  • [{n.category}] {n.title}: {n.message}" for n in unread_notifs]

        income = user.monthly_income or 0
        savings = income - total_expenses
        savings_rate = round((savings / income * 100) if income > 0 else 0, 1)
        budget = user.monthly_budget or 0

        lines = [
            f"Name: {user.full_name or user.username}",
            f"Monthly Income: ₹{income:,.0f}",
            f"Monthly Budget: ₹{budget:,.0f}",
            f"Total Expenses This Month: ₹{total_expenses:,.0f}",
            f"Net Savings This Month: ₹{savings:,.0f} ({savings_rate}% savings rate)",
            f"Budget Utilisation: {round(total_expenses/budget*100 if budget > 0 else 0, 1)}%",
            f"",
            f"Financial Health Score: {health.get('score', 'N/A')}/100 ({health.get('status', 'N/A')})",
            f"Savings Rate: {health.get('savings_rate', 0):.1f}% (Target: ≥ 20%)",
            f"Expense Ratio: {health.get('expense_ratio', 0):.1f}% (Target: ≤ 60%)",
            f"Investment Ratio: {health.get('investment_ratio', 0):.1f}% (Target: ≥ 10%)",
            f"Emergency Fund: {health.get('months_covered', 0):.1f} months covered (Target: ≥ 6)",
            f"Debt/EMI Ratio: {health.get('debt_ratio', 0):.1f}% (Target: ≤ 30%)",
            f"",
            f"Investment Portfolio Value: ₹{portfolio_value:,.0f}",
            f"Total Amount Invested: ₹{total_invested:,.0f}",
            f"Unrealised Gain/Loss: ₹{portfolio_value - total_invested:,.0f}",
            f"",
            f"Latest Loan Eligibility Run: {loan_line}",
        ]

        if goals_lines:
            lines.append("")
            lines.append("Active Financial Goals:")
            lines.extend(goals_lines)

        if txn_lines:
            lines.append("")
            lines.append("Recent Expenses:")
            lines.extend(txn_lines)

        if reco_lines:
            lines.append("")
            lines.append("Active AI Recommendations:")
            lines.extend(reco_lines)

        if notif_lines:
            lines.append("")
            lines.append("Unread Notifications:")
            lines.extend(notif_lines)

        if top_cats:
            lines.append("")
            lines.append("Top Spending Categories This Month:")
            for cat, amt in top_cats:
                pct = round(amt / total_expenses * 100 if total_expenses > 0 else 0, 1)
                lines.append(f"  • {cat}: ₹{amt:,.0f} ({pct}%)")

        if unpaid_bills:
            lines.append("")
            lines.append(f"Upcoming Unpaid Bills: {len(unpaid_bills)} bills totalling ₹{unpaid_total:,.0f}")
            for b in unpaid_bills[:3]:
                lines.append(f"  • {b.name}: ₹{b.amount:,.0f} due {b.due_date.strftime('%d %b') if b.due_date else 'N/A'}")

        return "\n".join(lines)

    except Exception as e:
        log.warning(f"Could not build financial context for user {user_id}: {e}")
        return ""


# ── Thread-safe client + session store ─────────────────────────────────────────

_client_lock = threading.Lock()
_client = None
_client_key = None

_sessions_lock = threading.Lock()
_sessions: dict = {}
_SESSION_TTL = 3600     # 1-hour idle TTL


def _get_client(api_key: str):
    global _client, _client_key
    from google import genai
    with _client_lock:
        if _client is None or _client_key != api_key:
            _client = genai.Client(api_key=api_key)
            _client_key = api_key
            log.info("Gemini client ready (google-genai)")
        return _client


def _session_key(session_id: str, lang: str) -> str:
    # BUG FIX: include lang in key to isolate EN and TA sessions
    return f"{session_id}_{lang}"


def clear_session(session_id: str, lang: str):
    """Public API — called when user clicks 'Clear Chat' to wipe server-side memory."""
    key = _session_key(session_id, lang)
    with _sessions_lock:
        _sessions.pop(key, None)
    log.info(f"Session cleared: {key}")


def _create_chat(client, lang: str, model_name: str, user_context: str = ""):
    from google.genai import types
    system = _build_system_prompt(lang, user_context)
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system,
            **GEN_CONFIG_KW,
        ),
    )


def _get_or_create_chat(session_id: str, lang: str, api_key: str,
                         model_name: str, user_context: str = ""):
    key = _session_key(session_id, lang)
    client = _get_client(api_key)

    with _sessions_lock:
        now = time.time()
        # Purge stale sessions
        stale = [k for k, v in _sessions.items() if now - v['last_used'] > _SESSION_TTL]
        for k in stale:
            del _sessions[k]

        entry = _sessions.get(key)

        # Invalidate if model changed
        if entry and entry.get('model') != model_name:
            del _sessions[key]
            entry = None

        if not entry:
            chat = _create_chat(client, lang, model_name, user_context)
            _sessions[key] = {
                'chat': chat,
                'model': model_name,
                'last_used': now,
                'message_count': 0,
                'user_context': user_context,
            }
            log.info(f"New AI session {key} using {model_name}")
        else:
            entry['last_used'] = now
            # Refresh context if it has changed (user updated their data)
            if user_context and entry.get('user_context') != user_context:
                # Recreate chat with fresh context on next >N message boundary
                entry['user_context'] = user_context

        return _sessions[key]['chat'], _sessions[key]


def _trim_history_if_needed(entry: dict, client, lang: str, model_name: str, user_context: str):
    """
    If conversation has exceeded MAX_HISTORY_MESSAGES, recreate the chat
    session with a condensed history (last 10 exchanges).
    This prevents the context window from growing unbounded.
    """
    if entry.get('message_count', 0) < MAX_HISTORY_MESSAGES:
        return
    try:
        # Get current history from the chat object
        old_chat = entry['chat']
        history = getattr(old_chat, '_history', None) or []
        # Keep only the last 10 message pairs (20 turns)
        trimmed = history[-20:] if len(history) > 20 else history

        from google.genai import types
        system = _build_system_prompt(lang, user_context)
        new_chat = client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=system,
                **GEN_CONFIG_KW,
            ),
            history=trimmed,
        )
        entry['chat'] = new_chat
        entry['message_count'] = len(trimmed)
        log.info(f"Session history trimmed to {len(trimmed)} messages")
    except Exception as e:
        log.warning(f"History trim failed (non-critical): {e}")


def _response_text(response) -> str:
    if response is None:
        return ""
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    return ""


# ── Main Chat Entry Point ──────────────────────────────────────────────────────

def ask_ai(question: str, lang: str = 'en',
           session_id: str = 'default', user_id: int = None) -> str:
    """
    Main chatbot function. Accepts a user question and returns an AI response.

    Args:
        question:   The user's message
        lang:       'en' or 'ta'
        session_id: Unique per-user session key (e.g. 'user_42_en')
        user_id:    Optional DB user ID — used to inject live financial context
    """
    if not question or not question.strip():
        return "Please ask a financial question and I'll be happy to help! 😊"

    api_key = _load_api_key()
    problem = _key_problem(api_key)

    if problem == "missing":
        log.warning("GEMINI_API_KEY not set — using offline advisor")
        return _fallback(question, lang)
    if problem == "placeholder":
        return (
            "**Gemini API key not configured.**\n\n"
            "1. Open https://aistudio.google.com/apikey\n"
            "2. Create a free API key\n"
            "3. Add to `.env`: `GEMINI_API_KEY=\"your-key\"`\n"
            "4. Restart the server (`Ctrl+C`, then `py -3 run.py`)"
        )
    if problem == "format":
        return (
            "**Unrecognized API key format.**\n\n"
            "Use a key from https://aistudio.google.com/apikey "
            "(starts with `AIza` or `AQ.`)."
        )

    question = question.strip()
    
    # ── Quick Intent Interceptors / Custom Responses ───────────────────────────
    q_lower = question.lower()
    
    # Intent 1: Report Comparison
    if 'compare' in q_lower and ('month' in q_lower or '202' in q_lower or 'vs' in q_lower or 'and' in q_lower):
        from app import ReportHistory
        from services.report_service import generate_ai_comparison
        # Attempt to find the last 2 reports for comparison
        user_reports = ReportHistory.query.filter_by(user_id=user_id).order_by(ReportHistory.created_at.desc()).limit(2).all()
        if len(user_reports) == 2:
            try:
                comp = generate_ai_comparison(user_id, user_reports[1].id, user_reports[0].id)
                return comp['narrative']
            except Exception as e:
                log.warning(f"Failed to auto-compare reports: {e}")
        else:
            return "To compare reports, please generate at least two historical reports first in the Report Studio page! 📊"

    # Intent 2: Goal tracking
    if any(w in q_lower for w in ['goal', 'laptop', 'macbook', 'trip', 'travel', 'wedding', 'retirement']):
        from app import Goal
        active_goals = Goal.query.filter_by(user_id=user_id, status='Active').all()
        if active_goals:
            lines = ["🎯 **Your WalletIQ Goals Roadmap & Action Plan:**", ""]
            for g in active_goals:
                prog = g.progress.first()
                prob = prog.success_probability if prog else 50.0
                lines.append(f"• **Goal**: {g.name} (Target: ₹{g.target_amount:,.0f})")
                lines.append(f"  - Current Savings: ₹{g.current_savings:,.0f} ({g.current_savings/g.target_amount*100:.1f}%)")
                lines.append(f"  - Monthly Target: ₹{g.monthly_contribution:,.0f}/month (Daily target: ₹{prog.daily_target if prog else 0:,.0f})")
                lines.append(f"  - Completion Success Probability: **{prob}%**")
                lines.append("")
            lines.append("💡 *Tip: You can set new savings goals directly in the Goal Planner dashboard.*")
            return "\n".join(lines)
        else:
            return "You haven't set any financial savings goals yet! 🎯 Open the Goal Planner in the sidebar to define one."

    # Intent 3: Spending Insights
    if any(w in q_lower for w in ['overspend', 'spend on', 'category', 'insight', 'subscription', 'duplicate']):
        from services.insight_service import generate_spending_insights_data
        data = generate_spending_insights_data(user_id)
        lines = ["📊 **WalletIQ AI Spending Patterns & Insights:**", ""]
        lines.append(f"• Total expenses this month: **₹{data['total_this_month']:,.2f}** ({data['percentage_change']:+.1f}% vs last month)")
        if data['fastest_growing_category'] != "None":
            lines.append(f"• Fastest growing category: **{data['fastest_growing_category']}** (+{data['fastest_growing_percentage']:.1f}%)")
        if data['ranked_categories']:
            lines.append(f"• Top Category: **{data['ranked_categories'][0]['category']}** (₹{data['ranked_categories'][0]['amount']:,.2f})")
        if data['suspected_subscriptions']:
            lines.append("• ⚠️ **Potential subscription waste detected**:")
            for sub in data['suspected_subscriptions']:
                lines.append(f"  - {sub['title']}: ₹{sub['amount']:,.0f} (recurring pattern)")
        return "\n".join(lines)


    # Build user context from DB (the key personalisation step)
    user_context = build_financial_context(user_id) if user_id else ""

    quota_errors = 0
    last_err = None

    for model_name in MODELS:
        try:
            client = _get_client(api_key)
            chat, entry = _get_or_create_chat(
                session_id, lang, api_key, model_name, user_context
            )

            # Trim history if we're at the limit
            _trim_history_if_needed(entry, client, lang, model_name, user_context)

            response = chat.send_message(question)
            entry['message_count'] = entry.get('message_count', 0) + 1

            text = _response_text(response)
            if text:
                return text

        except Exception as e:
            last_err = e
            if _is_quota_only(e):
                quota_errors += 1
            log.warning(f"Model {model_name} failed for session {session_id}: {e}")
            clear_session(session_id, lang)
            if _is_retryable(e):
                continue
            break

    if quota_errors == len(MODELS):
        return (
            "**Gemini free quota is used up for all models.**\n\n"
            "Your API key is valid. Please wait a few minutes and try again, or check usage at "
            "https://aistudio.google.com\n\n"
            "Meanwhile, here is offline guidance:\n\n" + _fallback(question, lang)
        )

    if last_err and any(x in str(last_err).lower() for x in ('api key', 'unauthenticated', '401', '403')):
        return (
            "**Gemini rejected the API key.**\n\n"
            "Create a new key at https://aistudio.google.com/apikey, "
            "update `.env`, and restart the server."
        )

    log.error(f"All Gemini models failed session={session_id}: {last_err}")
    return _fallback(question, lang)


# ── Offline Fallback ───────────────────────────────────────────────────────────

def _fallback(q: str, lang: str) -> str:
    """Rich rule-based fallback when Gemini is unavailable."""
    q_lower = q.lower()

    if lang == 'ta':
        if any(w in q_lower for w in ['சேமி', 'சேமிப்பு', 'பணம்', 'save']):
            return (
                "**💰 சேமிப்பு உத்திகள்:**\n\n"
                "• **50/30/20 விதி:** வருமானத்தில் 50% தேவைகளுக்கு, 30% விருப்பங்களுக்கு, 20% சேமிப்புக்கு\n"
                "• மாதம் ₹500 முதல் SIP தொடங்குங்கள் — Index Fund சிறந்தது\n"
                "• 6 மாத செலவை அவசர நிதியாக சேமியுங்கள்\n"
                "• சம்பளம் கிடைத்த உடனே சேமிக்கவும், மிச்சத்தை செலவழிக்கவும்\n\n"
                "**அடுத்த படிகள்:**\n"
                "• இந்த மாதம் ஒரு recurring deposit அல்லது SIP தொடங்குங்கள்\n"
                "• WalletIQ-ல் உங்கள் செலவுகளை தினமும் பதிவு செய்யுங்கள்"
            )
        if any(w in q_lower for w in ['முதலீடு', 'invest', 'sip', 'ppf', 'mutual']):
            return (
                "**📈 முதலீட்டு வழிகாட்டி:**\n\n"
                "• **Index Fund SIP** — குறைந்த கட்டணம், நீண்ட காலத்தில் சிறந்த வருமானம்\n"
                "• **PPF** — வரி இல்லாத 7.1% உத்தரவாத வருமானம் (ஆண்டுக்கு ₹1.5L வரை)\n"
                "• **NPS** — கூடுதல் ₹50,000 வரி சலுகை (80CCD)\n"
                "• **ELSS** — வரி சேமிப்பு + பங்கு சந்தை வளர்ச்சி\n\n"
                "**சிறந்த பங்கீடு:** 60% பங்கு, 30% கடன், 10% தங்கம்"
            )
        return (
            "**🤖 WalletIQ AI ஆலோசகர்** *(offline பயன்முறை)*\n\n"
            "தமிழில் உங்கள் நிதி கேள்விகளை கேளுங்கள்!\n\n"
            "• 💰 சேமிப்பு மற்றும் பட்ஜெட்\n"
            "• 📈 முதலீடு — SIP, PPF, NPS\n"
            "• 🏦 வரி திட்டமிடல்\n"
            "• 💳 கடன் மேலாண்மை"
        )

    # English fallback — rich, structured
    if any(w in q_lower for w in ['save', 'saving', 'savings', 'how much']):
        return (
            "**💰 Savings Strategy — The 3-Step Framework**\n\n"
            "**Step 1 — Calculate Your Savings Potential:**\n"
            "• Savings Rate = (Income − Expenses) ÷ Income × 100\n"
            "• Target: ≥ 20% of net income\n"
            "• Ideal: 30–40% for early wealth building\n\n"
            "**Step 2 — The 50/30/20 Rule:**\n"
            "• 50% → Fixed needs (rent, EMI, groceries, utilities)\n"
            "• 30% → Flexible wants (dining, entertainment, shopping)\n"
            "• 20% → Savings and investments (non-negotiable)\n\n"
            "**Step 3 — Automate It:**\n"
            "• Set up an auto-debit for SIP on salary day\n"
            "• Use a separate savings account to avoid spending it\n"
            "• Increase savings rate by 1% every 3 months\n\n"
            "**Quick Wins (₹2,000–₹5,000 saved instantly):**\n"
            "• Cancel unused subscriptions (OTT, gym, apps)\n"
            "• Cook 3 meals at home per week\n"
            "• Switch prepaid mobile plan — saves ₹200–500/month\n\n"
            "**Action Step:** Log into WalletIQ and check your current savings rate under Financial Health."
        )

    if any(w in q_lower for w in ['invest', 'sip', 'mutual fund', 'ppf', 'nps', 'stock', 'equity']):
        return (
            "**📈 Investment Guide for Indian Investors**\n\n"
            "**Beginner Portfolio (< ₹10,000/month):**\n"
            "• **Index Fund SIP** — 70% allocation. Nifty 50 or NIFTY Next 50. Low cost (0.1% expense ratio).\n"
            "• **PPF** — 20% allocation. Tax-free 7.1% guaranteed. Lock-in: 15 years.\n"
            "• **Emergency Fund** — 10% until 6 months of expenses saved.\n\n"
            "**Intermediate Portfolio (₹10k–₹50k/month):**\n"
            "• Index Funds: 50%, Mid-cap Fund: 20%\n"
            "• PPF + NPS: 20% (maximise 80C + 80CCD benefits)\n"
            "• Gold ETF: 10%\n\n"
            "**Tax-Smart Investments:**\n"
            "• Section 80C: Save up to ₹46,800 in tax (₹1.5L limit @ 31.2% bracket)\n"
            "• NPS 80CCD: Extra ₹15,600 tax saved on ₹50,000\n"
            "• ELSS: Best of 80C options — 3-year lock-in vs 15 for PPF\n\n"
            "⚠️ *Market-linked investments carry risk. Past performance does not guarantee future returns.*\n\n"
            "**Action Step:** Start with ₹500/month SIP in a Nifty 50 index fund — you can increase anytime."
        )

    if any(w in q_lower for w in ['tax', '80c', 'deduction', 'hra', 'regime', 'itr']):
        return (
            "**🏦 Tax Planning — Save ₹50,000–₹1,00,000 Legally**\n\n"
            "**Section 80C Deductions (Max ₹1.5 Lakhs):**\n"
            "• EPF contribution (auto-deducted from salary)\n"
            "• PPF investment (7.1% tax-free)\n"
            "• ELSS Mutual Fund (3-year lock-in, best returns)\n"
            "• LIC premium, home loan principal\n"
            "• Children's tuition fees\n\n"
            "**Additional Deductions:**\n"
            "• 80D: Health insurance — ₹25,000 self, ₹50,000 senior parents\n"
            "• 80CCD(1B): NPS — extra ₹50,000 above 80C\n"
            "• 24(b): Home loan interest — up to ₹2 Lakhs\n"
            "• HRA exemption if you pay rent\n\n"
            "**Old vs New Regime — Which Is Better?**\n"
            "• New Regime is better if you have **few deductions**\n"
            "• Old Regime is better if your **80C + HRA + 80D > ₹3.75L**\n"
            "• Calculate both — use the regime that gives lower tax\n\n"
            "**Action Step:** File ITR before July 31. Use WalletIQ's Financial Health section to track investments."
        )

    if any(w in q_lower for w in ['budget', 'expense', 'spend', 'overspend', 'category']):
        return (
            "**📊 Smart Budgeting System**\n\n"
            "**Zero-Based Budgeting (Best Method):**\n"
            "Every rupee gets a job: Income − All Allocations = ₹0\n\n"
            "**Recommended Category Limits (% of Net Income):**\n"
            "• Housing/Rent: ≤ 30%\n"
            "• Food & Groceries: ≤ 15%\n"
            "• Transport: ≤ 10%\n"
            "• Utilities & Bills: ≤ 10%\n"
            "• Entertainment/Dining: ≤ 10%\n"
            "• Health: ≤ 5%\n"
            "• **Savings & Investments: ≥ 20%**\n\n"
            "**Common Overspending Triggers:**\n"
            "• Dining out > ₹3,000/month — switch to meal prep\n"
            "• Impulse online shopping — use 24-hour rule\n"
            "• EMIs consuming > 40% of income — refinance or prepay\n\n"
            "**Action Step:** Set budgets for each category in WalletIQ. Review weekly."
        )

    if any(w in q_lower for w in ['emi', 'loan', 'credit card', 'debt', 'cibil']):
        return (
            "**💳 Debt & Loan Management Guide**\n\n"
            "**EMI Rules:**\n"
            "• Total EMIs should NOT exceed 40% of monthly income\n"
            "• Home loan EMI: ≤ 30% of income (most banks allow this max)\n"
            "• Personal/CC loans: Pay off first — they're most expensive\n\n"
            "**Credit Card Best Practices:**\n"
            "• Always pay the **full statement balance** (not minimum)\n"
            "• Minimum payment = interest trap at 36–42% p.a.\n"
            "• Keep credit utilisation below 30% to protect CIBIL score\n\n"
            "**Improve CIBIL Score:**\n"
            "• Pay all bills/EMIs on time (40% of score)\n"
            "• Keep CC utilisation < 30% (30% of score)\n"
            "• Don't close old credit cards\n"
            "• Avoid applying for multiple loans simultaneously\n\n"
            "**Debt Payoff Strategy — Avalanche Method:**\n"
            "• List all debts by interest rate (highest first)\n"
            "• Pay minimum on all, throw extra cash at highest rate first\n"
            "• Saves the most interest over time\n\n"
            "**Action Step:** Check WalletIQ's Loan Eligibility section to see your current debt-to-income ratio."
        )

    if any(w in q_lower for w in ['health score', 'financial health', 'wellbeing', 'health report', 'walletiq score']):
        return (
            "**❤️ Understanding Your Financial Health Score**\n\n"
            "WalletIQ's Financial Health Score (0–100) is calculated from 6 key metrics:\n\n"
            "| Metric | Your Score | Target |\n"
            "|---|---|---|\n"
            "| Savings Rate | Calculated from your data | ≥ 20% |\n"
            "| Expense Ratio | Calculated from your data | ≤ 60% |\n"
            "| Investment Ratio | Calculated from your data | ≥ 10% |\n"
            "| Budget Adherence | Based on your budgets | 100% |\n"
            "| Emergency Fund | Months of expenses saved | ≥ 6 months |\n"
            "| Debt Ratio | EMIs as % of income | ≤ 30% |\n\n"
            "**Score Ranges:**\n"
            "• 90–100: Excellent — You're in the top 5% of savers\n"
            "• 75–89: Good — Minor adjustments needed\n"
            "• 60–74: Fair — Focus on savings rate and debt reduction\n"
            "• Below 60: Needs Attention — Immediate budget review required\n\n"
            "**Action Step:** Visit the Financial Health section for your personalised score and AI recommendations."
        )

    # Generic fallback
    return (
        "**🤖 WalletIQ AI Financial Advisor** *(offline mode)*\n\n"
        "I'm here to help with all aspects of personal finance. Ask me about:\n\n"
        "• 💰 **Savings strategies** — How to save more every month\n"
        "• 📈 **Investments** — SIP, PPF, NPS, Mutual Funds, Stocks\n"
        "• 🏦 **Tax planning** — 80C, HRA, old vs new regime\n"
        "• 📊 **Budgeting** — Zero-based budgeting, category limits\n"
        "• 💳 **Debt management** — EMI, credit cards, CIBIL score\n"
        "• ❤️ **Financial health** — Understanding your score\n"
        "• 🏠 **Home loan** — Eligibility, EMI calculation, tax benefits\n"
        "• 🛡️ **Insurance** — Term life, health, vehicle coverage\n\n"
        "Type your question and I'll give you a detailed, personalised answer!"
    )


# ── Health Suggestions (for Financial Health page) ────────────────────────────

def generate_health_suggestions(stats: dict, lang: str = 'en') -> list:
    """
    Generates exactly 4 personalised financial recommendations using Gemini
    or rule-based fallback.
    """
    api_key = _load_api_key()
    problem = _key_problem(api_key)

    score = stats.get('score', 50)
    status = stats.get('status', 'Good')
    savings_rate = stats.get('savings_rate', 0.0)
    expense_ratio = stats.get('expense_ratio', 0.0)
    investment_ratio = stats.get('investment_ratio', 0.0)
    budget_score = stats.get('budget_score', 0.0)
    months_covered = stats.get('months_covered', 0.0)
    debt_ratio = stats.get('debt_ratio', 0.0)
    income = stats.get('income', 0)
    expenses = stats.get('expenses', 0)

    prompt = f"""Analyze these user financial metrics and generate exactly 4 highly personalised, actionable financial recommendations.

Financial Metrics:
- Overall Health Score: {score}/100 ({status})
- Savings Rate: {savings_rate:.1f}% (Target: ≥ 20%)
- Expense Ratio: {expense_ratio:.1f}% (Target: ≤ 60%)
- Investment Ratio: {investment_ratio:.1f}% (Target: ≥ 10%)
- Budget Adherence Score: {budget_score:.0f}/100 (Target: 100)
- Emergency Fund: {months_covered:.1f} months covered (Target: ≥ 6 months)
- Debt-to-Income (EMI) Ratio: {debt_ratio:.1f}% (Target: ≤ 30%)
- Monthly Income: ₹{income:,.0f}
- Monthly Expenses: ₹{expenses:,.0f}

Language: {'Tamil' if lang == 'ta' else 'English'}

Rules:
- Exactly 4 recommendations, each on its own line starting with a hyphen or asterisk
- Each must be specific, use actual ₹ numbers, and be under 20 words
- No headers, no numbering, no introductory text
- Use Indian Rupee (₹) only"""

    if problem:
        log.warning("Gemini API not available — using rule-based recommendations")
        return _fallback_suggestions(stats, lang)

    try:
        from google.genai import types
        client = _get_client(api_key)
        response = client.models.generate_content(
            model=MODELS[0],
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=500)
        )
        text = _response_text(response)
        if text:
            lines = [line.strip().lstrip('*-•').strip() for line in text.split('\n') if line.strip()]
            suggestions = [ln for ln in lines if ln and len(ln) > 10]
            if len(suggestions) >= 3:
                return suggestions[:4]
    except Exception as e:
        log.warning(f"Failed to generate Gemini suggestions: {e}")

    return _fallback_suggestions(stats, lang)


def _fallback_suggestions(stats: dict, lang: str) -> list:
    score = stats.get('score', 50)
    savings_rate = stats.get('savings_rate', 0.0)
    expense_ratio = stats.get('expense_ratio', 0.0)
    investment_ratio = stats.get('investment_ratio', 0.0)
    budget_score = stats.get('budget_score', 0.0)
    months_covered = stats.get('months_covered', 0.0)
    debt_ratio = stats.get('debt_ratio', 0.0)
    income = stats.get('income', 0)
    expenses = stats.get('expenses', 0)

    suggestions = []

    if lang == 'ta':
        if savings_rate < 20:
            suggestions.append(f"மாதாந்திர சேமிப்பை ₹{int(income * 0.2):,} ஆக உயர்த்துங்கள் (20% இலக்கு).")
        else:
            suggestions.append("சிறந்த சேமிப்பு விகிதம்! உபரி பணத்தை Mutual Funds-ல் முதலீடு செய்யுங்கள்.")
        if expense_ratio > 60:
            suggestions.append(f"செலவுகளை ₹{int(income * 0.5):,}க்கு கீழ் குறைக்க dining மற்றும் shopping செலவுகளை 15% குறைக்கவும்.")
        if investment_ratio < 10:
            suggestions.append("குறைந்தபட்சம் ₹2,000 உடன் Index Fund SIP தொடங்குங்கள்.")
        elif investment_ratio < 20:
            suggestions.append("SIP தொகையை மாதம் ₹1,000 உயர்த்தி கூட்டு வளர்ச்சியை அதிகரியுங்கள்.")
        if months_covered < 6:
            target = int(expenses * 6)
            suggestions.append(f"அவசர நிதி இலக்கு: ₹{target:,} (6 மாத செலவு). இது உங்கள் நிதி பாதுகாப்பின் அடித்தளம்.")
        if debt_ratio > 30:
            suggestions.append("EMI சுமையை 30%க்கு கீழ் கொண்டுவர அதிக வட்டி கடன்களை முதல் தீர்க்கவும்.")
        if len(suggestions) < 4:
            suggestions.append("Section 80C-ல் PPF அல்லது ELSS மூலம் ₹1.5L வரை வரி சேமியுங்கள்.")
        if len(suggestions) < 4:
            suggestions.append("WalletIQ-ல் வாராந்திர செலவு ஆய்வு நடத்தி பட்ஜெட் கட்டுப்பாட்டை மேம்படுத்துங்கள்.")
    else:
        if savings_rate < 20:
            target_savings = int(income * 0.2)
            suggestions.append(f"Increase monthly savings to ₹{target_savings:,} to reach the 20% savings rate target.")
        else:
            suggestions.append(f"Excellent {savings_rate:.0f}% savings rate! Redirect the surplus into equity SIPs for wealth compounding.")
        if expense_ratio > 60:
            suggestions.append(f"Expenses at {expense_ratio:.0f}% of income. Cut discretionary spending by 15% to save an extra ₹{int(income * 0.15):,}/month.")
        if investment_ratio < 10:
            suggestions.append("Start a ₹2,000/month Nifty 50 Index Fund SIP — the lowest-cost path to long-term wealth.")
        elif investment_ratio < 20:
            suggestions.append(f"Increase SIP allocation by ₹{int(income * 0.05):,}/month to reach the 20% investment target.")
        if months_covered < 6:
            target = int(expenses * 6)
            cur = int(expenses * months_covered)
            suggestions.append(f"Build emergency fund to ₹{target:,} (currently ₹{cur:,}). Target: 6 months of expenses.")
        elif months_covered < 3:
            suggestions.append(f"Emergency fund critically low at {months_covered:.1f} months. Prioritise building it to ₹{int(expenses * 6):,}.")
        if debt_ratio > 30:
            suggestions.append(f"EMI ratio at {debt_ratio:.0f}% of income. Prepay the highest-interest loan first to reduce debt burden below 30%.")
        if budget_score < 80:
            suggestions.append(f"Budget adherence at {budget_score:.0f}/100. Set category-wise limits in WalletIQ and review weekly.")
        if len(suggestions) < 4:
            suggestions.append("Maximise Section 80C (₹1.5L) via PPF/ELSS to reduce tax liability by up to ₹46,800.")
        if len(suggestions) < 4:
            suggestions.append("Conduct a weekly WalletIQ financial review to maintain 100% budget adherence and track savings progress.")

    return suggestions[:4]


# ── Savings Suggestions (for Savings Prediction page) ────────────────────────

def generate_savings_suggestions(stats: dict, forecast_data: dict, lang: str) -> list:
    api_key = _load_api_key()
    problem = _key_problem(api_key)

    mod_nw_1y = forecast_data['moderate']['savings_1y']
    mod_nw_5y = forecast_data['moderate']['savings_5y']
    agg_nw_1y = forecast_data['aggressive']['savings_1y']
    agg_nw_5y = forecast_data['aggressive']['savings_5y']
    con_nw_1y = forecast_data['conservative']['savings_1y']
    income = stats.get('income', 0)
    expenses = stats.get('expenses', 0)

    prompt = f"""Generate exactly 3 personalised, highly actionable savings optimisation suggestions based on these financials:

Current Financials:
- Monthly Income: ₹{income:,}
- Monthly Expenses: ₹{expenses:,}
- Net Savings Rate: {stats.get('savings_rate', 0):.1f}%
- Current Portfolio / Net Worth: ₹{forecast_data.get('current_savings', 0):,}

12-Month Projections:
- Conservative Track: ₹{con_nw_1y:,.0f}
- Moderate Track: ₹{mod_nw_1y:,.0f}
- Aggressive Track: ₹{agg_nw_1y:,.0f}
- Difference (Moderate vs Aggressive over 5 years): ₹{(agg_nw_5y - mod_nw_5y):,.0f}

Language: {'Tamil' if lang == 'ta' else 'English'}

Rules:
- Exactly 3 recommendations, one per line, starting with hyphen or asterisk
- Use actual ₹ numbers from the data above
- Each suggestion must be actionable and specific (< 20 words)
- No headers, no numbering, no intro text"""

    if problem:
        return _fallback_savings_suggestions(stats, forecast_data, lang)

    try:
        from google.genai import types
        client = _get_client(api_key)
        response = client.models.generate_content(
            model=MODELS[0],
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=400)
        )
        text = _response_text(response)
        if text:
            lines = [line.strip().lstrip('*-•').strip() for line in text.split('\n') if line.strip()]
            suggestions = [ln for ln in lines if ln and len(ln) > 10]
            if len(suggestions) >= 2:
                return suggestions[:3]
    except Exception as e:
        log.warning(f"Failed to generate Gemini savings suggestions: {e}")

    return _fallback_savings_suggestions(stats, forecast_data, lang)


def _fallback_savings_suggestions(stats: dict, forecast_data: dict, lang: str) -> list:
    mod_1y = forecast_data['moderate']['savings_1y']
    agg_1y = forecast_data['aggressive']['savings_1y']
    diff_1y = agg_1y - mod_1y
    agg_5y = forecast_data['aggressive']['savings_5y']
    mod_5y = forecast_data['moderate']['savings_5y']
    diff_5y = agg_5y - mod_5y
    income = stats.get('income', 0)

    if lang == 'ta':
        return [
            f"செலவுகளை 15% குறைத்தால், 1 வருடத்தில் ₹{int(diff_1y):,} கூடுதல் சேமிப்பு கிடைக்கும்.",
            f"தீவிர உத்தியில் 5 ஆண்டுகளில் சொத்து மதிப்பு ₹{int(agg_5y):,} — மிதமான உத்தியை விட ₹{int(diff_5y):,} அதிகம்.",
            f"மாத SIP-ஐ ₹{int(income * 0.05):,} உயர்த்தி கூட்டு வளர்ச்சியின் பலனை அதிகரியுங்கள்.",
        ]
    return [
        f"Cutting discretionary spending by 15% generates an extra ₹{int(diff_1y):,} in just 12 months.",
        f"The Aggressive track builds ₹{int(diff_5y):,} more wealth over 5 years vs Moderate — start now.",
        f"Redirect ₹{int(income * 0.05):,}/month from savings into active equity SIPs for compound growth.",
    ]
