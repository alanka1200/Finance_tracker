#!/usr/bin/env python
"""Сидинг тестовых данных для конкретного пользователя.

Использование:
    python scripts/seed.py <telegram_id>

Создаёт:
- 50 случайных транзакций за последние 30 дней
- 3 финансовые цели
- 2 инвестиции
"""
import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Добавляем путь к проекту
sys.path.insert(0, ".")

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Category,
    Goal,
    GoalPriority,
    Investment,
    InvestmentType,
    Transaction,
    TransactionKind,
    User,
)


async def seed(telegram_id: int) -> None:
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if not user:
            print(f"❌ Пользователь tg={telegram_id} не найден. Запусти Mini App один раз, чтобы зарегистрироваться.")
            return

        # Категории пользователя
        cats = (
            await db.execute(
                select(Category).where(Category.user_id == user.id, Category.deleted_at.is_(None))
            )
        ).scalars().all()
        income_cats = [c for c in cats if c.kind == "income" or c.kind.value == "income"]
        expense_cats = [c for c in cats if c.kind == "expense" or c.kind.value == "expense"]

        if not income_cats or not expense_cats:
            print("❌ У пользователя нет категорий")
            return

        # 50 случайных транзакций
        for i in range(50):
            is_income = random.random() < 0.25  # 25% доходов, 75% расходов
            cat_pool = income_cats if is_income else expense_cats
            kind = TransactionKind.INCOME if is_income else TransactionKind.EXPENSE

            amount = (
                random.choice([5000, 12000, 50000, 80000, 100000])
                if is_income
                else random.choice([100, 250, 500, 1500, 3000, 8000, 15000])
            )

            tx = Transaction(
                user_id=user.id,
                kind=kind,
                amount=Decimal(str(amount + random.randint(-50, 50))),
                currency="RUB",
                category_id=random.choice(cat_pool).id,
                description=random.choice(
                    [
                        None,
                        "Заказ в Wildberries",
                        "Кофе в Старбаксе",
                        "Зарплата за проект",
                        "Обед в столовой",
                        "Подписка на сервис",
                    ]
                ),
                occurred_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23)),
            )
            db.add(tx)

        # 3 цели
        goals_data = [
            ("🏠 Первый взнос", Decimal("1000000"), Decimal("250000"), GoalPriority.HIGH, "🏠"),
            ("✈️ Отпуск в Тае", Decimal("150000"), Decimal("60000"), GoalPriority.MEDIUM, "✈️"),
            ("💻 Новый MacBook", Decimal("250000"), Decimal("180000"), GoalPriority.MEDIUM, "💻"),
        ]
        for title, target, current, prio, icon in goals_data:
            goal = Goal(
                user_id=user.id,
                title=title,
                target_amount=target,
                current_amount=current,
                currency="RUB",
                priority=prio,
                icon=icon,
                deadline=(datetime.now() + timedelta(days=random.randint(60, 365))).date(),
            )
            db.add(goal)

        # 2 инвестиции
        investments_data = [
            (InvestmentType.STOCK, "Сбербанк", "SBER", Decimal("100000")),
            (InvestmentType.CRYPTO, "Bitcoin", "BTC", Decimal("50000")),
        ]
        for typ, name, ticker, amount in investments_data:
            inv = Investment(
                user_id=user.id,
                type=typ,
                name=name,
                ticker=ticker,
                purchase_amount=amount,
                quantity=Decimal("1"),
                purchase_date=(datetime.now() - timedelta(days=random.randint(30, 180))).date(),
                current_value=amount * Decimal(str(random.uniform(0.85, 1.25))),
                currency="RUB",
            )
            db.add(inv)

        await db.commit()
        print(f"✅ Создано: 50 транзакций, 3 цели, 2 инвестиции для tg={telegram_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("Использование: python scripts/seed.py <telegram_id>")
        sys.exit(1)
    asyncio.run(seed(int(sys.argv[1])))
