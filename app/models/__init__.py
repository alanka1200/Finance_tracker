"""ORM модели приложения. Все модели наследуют app.db.Base."""
from app.models.category import DEFAULT_CATEGORIES, Category, CategoryKind
from app.models.goal import Goal, GoalPriority, GoalStatus
from app.models.investment import Investment, InvestmentType
from app.models.referral import Referral, ReferralStatus
from app.models.transaction import Transaction, TransactionKind
from app.models.user import User

__all__ = [
    "DEFAULT_CATEGORIES",
    "Category",
    "CategoryKind",
    "Goal",
    "GoalPriority",
    "GoalStatus",
    "Investment",
    "InvestmentType",
    "Referral",
    "ReferralStatus",
    "Transaction",
    "TransactionKind",
    "User",
]
