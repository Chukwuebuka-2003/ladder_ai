import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import Any

from database import get_db
from models import User, Expense
from schemas import ChatMessage, ChatResponse, ExpenseCreate
from services.deps import get_current_user
from services import nlu_service, expense_service, ai_service
from core.datetime_utils import parse_time_range

logger = logging.getLogger(__name__)
router = APIRouter()

def _safe_float_conversion(value: Any, default: float = 0.0) -> float:
    if value is None: return default
    try: return float(value)
    except (ValueError, TypeError): return default

def _get_suggestions_intent(db: Session, user: User, entities: dict) -> str:
    """Analyzes spending from two periods and generates actionable advice."""
    today = date.today()
    current_end_date, current_start_date = today, today - timedelta(days=30)
    previous_end_date, previous_start_date = current_start_date - timedelta(days=1), current_start_date - timedelta(days=31)

    current_expenses = db.query(Expense).filter(Expense.user_id == user.id, Expense.date.between(current_start_date, current_end_date)).all()
    if not current_expenses: return "I don't have enough recent spending data to provide suggestions."

    previous_expenses = db.query(Expense).filter(Expense.user_id == user.id, Expense.date.between(previous_start_date, previous_end_date)).all()

    current_data = [{"description": e.description, "amount": e.amount, "category": e.category} for e in current_expenses]
    previous_data = [{"description": p.description, "amount": p.amount, "category": p.category} for p in previous_expenses]

    return ai_service.get_suggestions_using_ai(
        current_period_expenses=current_data,
        previous_period_expenses=previous_data,
        current_start_date=current_start_date.isoformat(),
        current_end_date=current_end_date.isoformat(),
        previous_start_date=previous_start_date.isoformat(),
        previous_end_date=previous_end_date.isoformat()
    )

def _get_comprehensive_summary_intent(db: Session, user: User, entities: dict) -> str:
    """Gathers multiple insights and synthesizes them into a single response."""
    start_date, end_date = parse_time_range(entities.get("time_range"))
    time_desc = "in " + (entities.get("time_range") or "the last 30 days")
    query = db.query(Expense).filter(Expense.user_id == user.id, Expense.date.between(start_date, end_date))

    if not query.first(): return f"I couldn't find any expenses to summarize for {time_desc}."

    total_spent = query.with_entities(func.sum(Expense.amount)).scalar()
    most_expensive = query.order_by(Expense.amount.desc()).first()
    cheapest_item = query.order_by(Expense.amount.asc()).first()
    category_query = db.query(Expense.category, func.sum(Expense.amount).label('total')).filter(
        Expense.user_id == user.id, Expense.date.between(start_date, end_date)
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    top_category = category_query[0] if category_query else None
    lowest_category = category_query[-1] if category_query else None

    response = f"Here is a summary of your spending {time_desc}:\n"
    response += f"- You spent a total of ${_safe_float_conversion(total_spent):.2f}.\n"
    if most_expensive: response += f"- Your most expensive purchase was '{most_expensive.description}' for ${most_expensive.amount:.2f}.\n"
    if cheapest_item: response += f"- Your cheapest purchase was '{cheapest_item.description}' for ${cheapest_item.amount:.2f}.\n"
    if top_category: response += f"- Your top spending category was '{top_category[0] or 'Uncategorized'}' with a total of ${top_category[1]:.2f}.\n"
    if lowest_category and lowest_category != top_category: response += f"- Your lowest spending category was '{lowest_category[0] or 'Uncategorized'}' with a total of ${lowest_category[1]:.2f}."
    return response.strip()

def _handle_query_intent(db: Session, user: User, entities: dict) -> str:
    """
    --- THIS FUNCTION IS UPGRADED ---
    Constructs and executes a database query based on extracted NLU entities.
    """
    target, operation = entities.get("target"), entities.get("operation")
    time_range_str, limit = entities.get("time_range"), entities.get("limit", 5)
    start_date, end_date = parse_time_range(time_range_str)
    query = db.query(Expense).filter(Expense.user_id == user.id, Expense.date.between(start_date, end_date))
    time_desc = "in " + (time_range_str or "the last 30 days")

    # New: Handle specific item searches
    if operation == "search":
        search_query = query.filter(Expense.description.ilike(f"%{target}%"))
        results = search_query.all()
        if not results:
            return f"No, I couldn't find any expenses for '{target}' {time_desc}."

        total = search_query.with_entities(func.sum(Expense.amount)).scalar()
        response = f"Yes, you spent a total of ${_safe_float_conversion(total):.2f} on '{target}' {time_desc}. Here are the transactions I found:\n"
        for exp in results:
            response += f"- ${exp.amount:.2f} on {exp.date.strftime('%Y-%m-%d')}\n"
        return response.strip()

    if target in ["item", "transaction"]:
        if operation == "highest":
            result = query.order_by(Expense.amount.desc()).first()
            return f"Your most expensive purchase {time_desc} was '{result.description}' for ${result.amount:.2f}." if result else f"I found no expenses {time_desc}."
        if operation == "lowest":
            result = query.order_by(Expense.amount.asc()).first()
            return f"Your cheapest purchase {time_desc} was '{result.description}' for ${result.amount:.2f}." if result else f"I found no expenses {time_desc}."
        if operation == "list":
            results = query.order_by(Expense.date.desc()).limit(limit).all()
            if not results: return f"I found no expenses {time_desc}."
            lines = [f"Here are your last {len(results)} transactions:"] + [f"- ${e.amount:.2f} for '{e.description}' on {e.date.strftime('%Y-%m-%d')}" for e in results]
            return "\n".join(lines)

    if target == "category" or operation == "top":
        category_q = db.query(Expense.category, func.sum(Expense.amount).label('total')).filter(
            Expense.user_id == user.id, Expense.date.between(start_date, end_date)
        ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).limit(limit).all()
        if not category_q: return f"I found no spending to categorize {time_desc}."
        lines = [f"Here are your top {len(category_q)} spending categories {time_desc}:"] + [f"- {cat or 'Uncategorized'}: ${total:.2f}" for cat, total in category_q]
        return "\n".join(lines)

    if target and operation == "total":
        total = query.filter(Expense.category.ilike(f"%{target}%")).with_entities(func.sum(Expense.amount)).scalar()
        return f"You spent ${_safe_float_conversion(total):.2f} on '{target}' {time_desc}."

    total = query.with_entities(func.sum(Expense.amount)).scalar()
    return f"Your total spending {time_desc} was ${_safe_float_conversion(total):.2f}."

def _get_insights_intent(db: Session, user: User, entities: dict) -> str:
    """Handles general, AI-driven insight queries."""
    start_date, end_date = parse_time_range(entities.get("time_range"))
    expenses = db.query(Expense).filter(Expense.user_id == user.id, Expense.date.between(start_date, end_date)).all()
    if not expenses: return "I couldn't find any expenses for that period to analyze."

    expenses_data = [{"amount": e.amount, "description": e.description, "category": e.category, "date": e.date.isoformat()} for e in expenses]
    insights = ai_service.get_insights_using_ai(user.id, start_date, end_date, expenses_data, "gemini")

    total = _safe_float_conversion(insights.get('total_spent'))
    response = f"In that period, you've spent a total of ${total:.2f}. "
    if insights.get('top_categories'):
        top_cat = insights['top_categories'][0]['category']
        response += f"Your top spending category was '{top_cat}'."
    return response

def _add_expense_intent(db: Session, user: User, entities: dict) -> str:
    """Handles the 'add_expense' intent."""
    amount, desc = _safe_float_conversion(entities.get("amount")), entities.get("description")
    if not amount or not desc: return "I'm missing the amount or description."
    if amount <= 0: return "The expense amount must be a positive number."

    expense_data = ExpenseCreate(amount=amount, description=str(desc), date=datetime.now())
    expense_service.create_expense(db=db, expense_create=expense_data, user_id=user.id)
    return f"Got it. I've added an expense of ${amount:.2f} for '{desc}'."

def _greeting_intent(user: User, entities: dict) -> str:
    return "Hello there! How can I help you?"

def _fallback_intent(user: User, entities: dict) -> str:
    return "I'm sorry, I didn't quite understand that."

INTENT_HANDLERS = {
    "add_expense": _add_expense_intent,
    "get_insights": _get_insights_intent,
    "query": _handle_query_intent,
    "get_comprehensive_summary": _get_comprehensive_summary_intent,
    "get_suggestions": _get_suggestions_intent,
    "greeting": _greeting_intent,
}

@router.post("/", response_model=ChatResponse)
async def handle_chat_message(request: ChatMessage, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not request.message: return ChatResponse(message="Please say something!")

    nlu_result = nlu_service.parse_message(request.message)
    intent, entities = nlu_result.get("intent"), nlu_result.get("entities", {})
    logger.info(f"NLU Result - Intent: {intent}, Entities: {entities}")

    handler = INTENT_HANDLERS.get(intent, _fallback_intent)

    if intent in ["add_expense", "get_insights", "query", "get_comprehensive_summary", "get_suggestions"]:
        response_message = handler(db=db, user=current_user, entities=entities)
    else:
        response_message = handler(user=current_user, entities=entities)

    return ChatResponse(message=response_message)
