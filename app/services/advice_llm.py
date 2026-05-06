"""Генератор финансовых советов.

Гибридный подход:
1. Rule-based движок ВСЕГДА работает — это базовый слой, не требует API ключей.
2. Если задан GROQ_API_KEY (или CEREBRAS / GEMINI) — используется LLM поверх правил
   как "приукрашивание" + персонализация. Если LLM недоступен → отдаём rules.

Это даёт продукту работоспособность с нуля и плавный апгрейд при наличии API.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.schemas.analytics import AdviceResponse, DashboardData


class RuleEngine:
    """Базовый движок советов на правилах. Никаких API."""

    def analyze(self, dashboard: DashboardData) -> tuple[list[str], str]:
        """Возвращает (insights, fallback_text). insights — короткие тезисы."""
        insights: list[str] = []
        income = dashboard.income_this_month
        expense = dashboard.expense_this_month
        balance = dashboard.balance

        # 1. Соотношение доходов/расходов
        if income > 0:
            spend_ratio = float(expense / income)
            if spend_ratio > 1.0:
                insights.append(
                    f"⚠️ Вы тратите больше, чем зарабатываете ({spend_ratio*100:.0f}% от дохода). "
                    "Это первый шаг к долгам — пересмотрите крупные категории расходов."
                )
            elif spend_ratio > 0.9:
                insights.append(
                    f"📊 Расходы ({spend_ratio*100:.0f}% от дохода) близки к критическим. "
                    "Рекомендуется откладывать минимум 10–20% дохода."
                )
            elif spend_ratio < 0.5:
                insights.append(
                    f"✅ Отличное соотношение: расходы всего {spend_ratio*100:.0f}% от дохода. "
                    "Самое время направить излишки в инвестиции или подушку безопасности."
                )
            else:
                insights.append(
                    f"💡 Норма расходов: {spend_ratio*100:.0f}%. "
                    "Старайтесь откладывать 20% — правило 50/30/20."
                )

        # 2. Анализ баланса
        if balance < 0:
            insights.append(
                "🔴 Совокупный баланс отрицательный. Сфокусируйтесь на сокращении ненужных трат "
                "и закройте долги до начала инвестиций."
            )
        elif balance < income * Decimal("3"):
            insights.append(
                "🛡️ Подушка безопасности ниже рекомендуемых 3–6 месячных доходов. "
                "Это первая инвестиция, которую стоит сделать."
            )

        # 3. Топ-категории расходов
        if dashboard.top_expense_categories:
            top = dashboard.top_expense_categories[0]
            if top.percent > 40:
                insights.append(
                    f"⚡ Категория '{top.category_icon} {top.category_name}' "
                    f"съедает {top.percent:.0f}% всех расходов. Один источник трат — это риск; "
                    "подумайте, где можно ужать."
                )

        # 4. Цели
        if dashboard.active_goals_count == 0:
            insights.append(
                "🎯 У вас нет активных финансовых целей. Цель — это конкретика: "
                "'отложить 100 000 ₽ к декабрю' работает лучше, чем 'копить'."
            )

        # 5. Инвестиции
        if dashboard.investments_total_value == 0 and balance > income * Decimal("2"):
            insights.append(
                "📈 У вас есть свободные средства, но нет инвестиций. "
                "Начните с малого: ОФЗ или индексный ETF."
            )

        # 6. Реферальная мотивация
        if dashboard.referrals_count == 0 and dashboard.transactions_count > 10:
            insights.append(
                "🤝 Поделитесь приложением с друзьями через свою реферальную ссылку — "
                "вы получите бонусы за каждого приглашённого."
            )

        if not insights:
            insights.append(
                "🌱 Вы только начинаете отслеживать финансы. Добавьте больше транзакций — "
                "и я смогу дать более точные рекомендации."
            )

        # Сборка fallback-текста (когда нет LLM)
        text = "\n\n".join(insights)
        return insights, text


class LLMClient:
    """Универсальный клиент LLM с fallback-цепочкой Groq → Cerebras → Gemini."""

    SYSTEM_PROMPT = (
        "Ты — дружелюбный персональный финансовый советник в Telegram-приложении. "
        "Отвечай ТОЛЬКО на русском языке, кратко (3–5 предложений), конкретно и без воды. "
        "Никогда не давай советов по покупке или продаже конкретных ценных бумаг. "
        "Не упоминай, что ты ИИ или языковая модель. Используй эмодзи умеренно."
    )

    async def generate(self, prompt: str) -> tuple[str, str] | None:
        """Возвращает (text, source) или None, если все провайдеры недоступны."""
        # Пробуем по порядку
        for provider, fn in [
            ("groq", self._call_groq),
            ("cerebras", self._call_cerebras),
            ("gemini", self._call_gemini),
        ]:
            try:
                result = await fn(prompt)
                if result:
                    return result, provider
            except Exception as e:
                logger.warning(f"LLM провайдер {provider} упал: {e}")
                continue
        return None

    async def _call_groq(self, prompt: str) -> str | None:
        if not settings.groq_api_key:
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600,
                },
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _call_cerebras(self, prompt: str) -> str | None:
        if not settings.cerebras_api_key:
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.cerebras_api_key}"},
                json={
                    "model": settings.cerebras_model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600,
                },
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _call_gemini(self, prompt: str) -> str | None:
        if not settings.gemini_api_key:
            return None
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                url,
                json={
                    "system_instruction": {"parts": [{"text": self.SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
                },
            )
            r.raise_for_status()
            data = r.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError):
                return None


def _format_dashboard_for_llm(d: DashboardData) -> str:
    """Сериализует дашборд в человекочитаемый prompt-кусок."""
    parts = [
        f"Баланс: {d.balance:.0f} ₽",
        f"Доход за месяц: {d.income_this_month:.0f} ₽",
        f"Расход за месяц: {d.expense_this_month:.0f} ₽",
        f"Всего транзакций: {d.transactions_count}",
        f"Активных целей: {d.active_goals_count}",
        f"Стоимость инвестиций: {d.investments_total_value:.0f} ₽",
    ]
    if d.top_expense_categories:
        parts.append("Топ категорий расходов в этом месяце:")
        for c in d.top_expense_categories[:5]:
            parts.append(f"  - {c.category_icon} {c.category_name}: {c.total:.0f} ₽ ({c.percent:.1f}%)")
    return "\n".join(parts)


async def generate_advice(dashboard: DashboardData) -> AdviceResponse:
    """Главная точка входа: генерирует совет на основе дашборда."""
    rule_engine = RuleEngine()
    insights, fallback_text = rule_engine.analyze(dashboard)

    # Пробуем LLM
    llm = LLMClient()
    user_summary = _format_dashboard_for_llm(dashboard)
    insights_block = "\n".join(f"- {i}" for i in insights)
    prompt = (
        "Сформулируй персональный финансовый совет для пользователя на основе его данных.\n\n"
        f"=== Финансовая сводка ===\n{user_summary}\n\n"
        f"=== Выявленные паттерны (от системы аналитики) ===\n{insights_block}\n\n"
        "Дай совет в 3–5 предложениях. Будь конкретен и поддержи пользователя."
    )

    llm_result = await llm.generate(prompt)
    if llm_result:
        text, source = llm_result
        return AdviceResponse(text=text, source=source, insights=insights)

    # Никакой LLM не сработал → возвращаем rule-based текст
    return AdviceResponse(text=fallback_text, source="rules", insights=insights)
