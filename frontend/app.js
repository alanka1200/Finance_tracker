/**
 * Главный модуль Mini App. Bootstrap, рендеринг, обработчики.
 */

class App {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.charts = {}; // canvas -> Chart instance
        this.txFilter = { kind: 'all', search: '', page: 1 };
        this.txItems = [];
        this.balanceVisible = true;
    }

    async init() {
        try {
            // Инициализация Telegram WebApp
            if (this.tg) {
                this.tg.ready();
                this.tg.expand();
                this.tg.enableClosingConfirmation?.();
                // Цвет header'а — тема приложения
                try {
                    this.tg.setHeaderColor?.('secondary_bg_color');
                } catch {}
            }

            this.updateSplashStatus('Подключаемся к серверу...');
            await window.api.init();

            this.updateSplashStatus('Авторизация...');
            // Пробуем сразу обновить токен или авторизоваться
            try {
                await window.api.me();
            } catch (e) {
                if (e.status === 401 || !window.api.accessToken) {
                    await window.api.authenticate();
                } else {
                    throw e;
                }
            }

            this.updateSplashStatus('Загружаем данные...');
            await this.loadAllData();

            this.bindEvents();
            ui.setCurrentDate();
            this.hideSplash();
        } catch (e) {
            console.error('Ошибка инициализации:', e);
            this.updateSplashStatus(`❌ ${e.message || 'Ошибка'}`);
        }
    }

    updateSplashStatus(text) {
        const el = document.getElementById('splashStatus');
        if (el) el.textContent = text;
    }

    hideSplash() {
        const splash = document.getElementById('splash');
        const app = document.getElementById('app');
        const nav = document.getElementById('bottomNav');

        splash?.classList.add('hide');
        if (app) app.hidden = false;
        if (nav) nav.hidden = false;

        setTimeout(() => splash?.remove(), 600);
    }

    async loadAllData() {
        // Параллельная загрузка
        const [me, dashboard, advice] = await Promise.allSettled([
            window.api.me(),
            window.api.dashboard(),
            window.api.advice(),
        ]);

        if (me.status === 'fulfilled') {
            window.api.user = me.value;
            this.renderUser(me.value);
        }

        if (dashboard.status === 'fulfilled') {
            this.renderDashboard(dashboard.value);
        } else {
            console.error('Ошибка дашборда:', dashboard.reason);
        }

        if (advice.status === 'fulfilled') {
            this.renderAdvice(advice.value);
        } else {
            this.renderAdviceError();
        }
    }

    renderUser(user) {
        const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || 'Пользователь';
        document.getElementById('userName').textContent = fullName;
        document.getElementById('profileName').textContent = fullName;
        document.getElementById('profileUsername').textContent = user.username ? `@${user.username}` : `id ${user.telegram_id}`;
        document.getElementById('referralCode').textContent = user.referral_code || '—';

        // Аватар: первая буква имени
        const initial = (user.first_name?.[0] || user.username?.[0] || '?').toUpperCase();
        document.getElementById('profileAvatar').textContent = initial;
    }

    renderDashboard(data) {
        // Баланс
        document.getElementById('balanceAmount').textContent = ui.formatMoney(data.balance);
        document.getElementById('monthIncome').textContent = ui.formatMoney(data.income_this_month);
        document.getElementById('monthExpense').textContent = ui.formatMoney(data.expense_this_month);

        // Виджеты
        document.getElementById('statTransactions').textContent = data.transactions_count;
        document.getElementById('statGoals').textContent = data.active_goals_count;
        document.getElementById('statInvestments').textContent = ui.formatMoney(data.investments_total_value);
        document.getElementById('statReferrals').textContent = data.referrals_count;

        // Тренд
        this.renderTrendChart(data.last_30_days_trend);
        // Топ категорий
        this.renderExpenseChart(data.top_expense_categories);
        this.renderTopCategoriesList(data.top_expense_categories);
    }

    renderTrendChart(points) {
        const canvas = document.getElementById('trendChart');
        if (!canvas) return;
        this.charts.trend?.destroy();

        const labels = points.map(p => {
            const d = new Date(p.day);
            return d.getDate();
        });
        const incomes = points.map(p => Number(p.income));
        const expenses = points.map(p => Number(p.expense));

        this.charts.trend = new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Доход',
                        data: incomes,
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.15)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                    },
                    {
                        label: 'Расход',
                        data: expenses,
                        borderColor: '#f44336',
                        backgroundColor: 'rgba(244, 67, 54, 0.15)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ui.formatMoney(ctx.parsed.y)}`,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            font: { size: 10 },
                            callback: (v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v,
                        },
                    },
                    x: { ticks: { font: { size: 10 }, maxRotation: 0 } },
                },
            },
        });
    }

    renderExpenseChart(categories) {
        const canvas = document.getElementById('expenseChart');
        if (!canvas) return;
        this.charts.expense?.destroy();

        if (!categories || categories.length === 0) {
            canvas.parentElement.innerHTML = '<div class="empty-state"><i class="fas fa-chart-pie"></i><div class="empty-state-text">Нет расходов в этом месяце</div></div>';
            return;
        }

        this.charts.expense = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: categories.map(c => `${c.category_icon} ${c.category_name}`),
                datasets: [{
                    data: categories.map(c => Number(c.total)),
                    backgroundColor: categories.map(c => c.category_color),
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ui.formatMoney(ctx.parsed)} (${categories[ctx.dataIndex].percent.toFixed(1)}%)`,
                        },
                    },
                },
            },
        });
    }

    renderTopCategoriesList(categories) {
        const list = document.getElementById('topCategoriesList');
        if (!list) return;

        if (!categories || categories.length === 0) {
            list.innerHTML = '';
            return;
        }

        list.innerHTML = categories.map(c => `
            <div class="category-item">
                <div class="category-item-icon" style="background:${c.category_color}">${c.category_icon}</div>
                <div class="category-item-info">
                    <div>
                        <div class="category-item-name">${ui.escapeHtml(c.category_name)}</div>
                        <div class="category-item-percent">${c.count} ${this.txWord(c.count)} • ${c.percent.toFixed(1)}%</div>
                    </div>
                    <div class="category-item-amount">${ui.formatMoney(c.total)}</div>
                </div>
            </div>
        `).join('');
    }

    txWord(n) {
        const last = n % 10;
        const last2 = n % 100;
        if (last2 >= 11 && last2 <= 14) return 'транзакций';
        if (last === 1) return 'транзакция';
        if (last >= 2 && last <= 4) return 'транзакции';
        return 'транзакций';
    }

    renderAdvice(advice) {
        const body = document.getElementById('adviceBody');
        if (!body) return;
        const sourceLabel = {
            groq: 'AI (Groq)',
            cerebras: 'AI (Cerebras)',
            gemini: 'AI (Gemini)',
            rules: 'Анализ',
        }[advice.source] || 'Анализ';

        body.innerHTML = `
            <div>${this.formatAdviceText(advice.text)}</div>
            <div style="margin-top: 10px; font-size: 11px; opacity: 0.7;">— ${sourceLabel}</div>
        `;
    }

    formatAdviceText(text) {
        // Простой markdown-like рендеринг переносов
        return ui.escapeHtml(text).replace(/\n/g, '<br>');
    }

    renderAdviceError() {
        const body = document.getElementById('adviceBody');
        if (body) body.innerHTML = '<div class="empty-state-text">Не удалось загрузить совет</div>';
    }

    // ===== Транзакции =====
    async loadTransactions(reset = true) {
        if (reset) {
            this.txFilter.page = 1;
            this.txItems = [];
        }

        const list = document.getElementById('transactionsList');
        if (reset) {
            list.innerHTML = `
                <div class="skeleton" style="height: 60px;"></div>
                <div class="skeleton" style="height: 60px;"></div>
                <div class="skeleton" style="height: 60px;"></div>
            `;
        }

        try {
            const params = {
                page: this.txFilter.page,
                page_size: 20,
            };
            if (this.txFilter.kind && this.txFilter.kind !== 'all') params.kind = this.txFilter.kind;
            if (this.txFilter.search) params.search = this.txFilter.search;

            const res = await window.api.listTransactions(params);
            this.txItems = reset ? res.items : [...this.txItems, ...res.items];

            this.renderTransactionsList();
            document.getElementById('loadMoreBtn').style.display = res.has_more ? 'flex' : 'none';
        } catch (e) {
            list.innerHTML = `<div class="empty-state"><i class="fas fa-times-circle"></i><div>Ошибка загрузки: ${ui.escapeHtml(e.message)}</div></div>`;
        }
    }

    renderTransactionsList() {
        const list = document.getElementById('transactionsList');
        if (this.txItems.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-receipt"></i>
                    <div class="empty-state-title">Транзакций пока нет</div>
                    <div class="empty-state-text">Добавьте первую через быстрые действия на главной</div>
                </div>
            `;
            return;
        }

        // Группировка по дням
        const byDay = new Map();
        for (const tx of this.txItems) {
            const day = new Date(tx.occurred_at).toDateString();
            if (!byDay.has(day)) byDay.set(day, []);
            byDay.get(day).push(tx);
        }

        list.innerHTML = '';
        for (const [day, txs] of byDay) {
            const dayHeader = document.createElement('div');
            dayHeader.className = 'category-item-percent';
            dayHeader.style.cssText = 'padding: 8px 4px; font-weight: 600;';
            const d = new Date(day);
            const today = new Date();
            const ydy = new Date(Date.now() - 86400000);
            const sameDate = (a, b) => a.toDateString() === b.toDateString();
            dayHeader.textContent = sameDate(d, today)
                ? 'Сегодня'
                : sameDate(d, ydy)
                    ? 'Вчера'
                    : d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
            list.appendChild(dayHeader);

            for (const tx of txs) {
                const item = document.createElement('div');
                item.className = 'transaction-item';
                item.dataset.id = tx.id;
                const sign = tx.kind === 'income' ? '+' : '−';
                const cls = tx.kind === 'income' ? 'income' : 'expense';
                const color = tx.category_color || (tx.kind === 'income' ? '#4CAF50' : '#f44336');
                const icon = tx.category_icon || (tx.kind === 'income' ? '💰' : '💸');

                item.innerHTML = `
                    <div class="transaction-icon" style="background:${color}">${icon}</div>
                    <div class="transaction-info">
                        <div class="transaction-title">${ui.escapeHtml(tx.description || tx.category_name || 'Без описания')}</div>
                        <div class="transaction-meta">${ui.escapeHtml(tx.category_name || '')} • ${ui.formatDate(tx.occurred_at)}</div>
                    </div>
                    <div class="transaction-amount ${cls}">${sign}${ui.formatMoney(tx.amount, tx.currency)}</div>
                `;
                item.onclick = () => ui.openTxModal(tx.kind, tx);
                list.appendChild(item);
            }
        }
    }

    // ===== Цели =====
    async loadGoals() {
        const list = document.getElementById('goalsList');
        list.innerHTML = '<div class="skeleton" style="height: 100px;"></div>';

        try {
            const goals = await window.api.listGoals();
            if (goals.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-bullseye"></i>
                        <div class="empty-state-title">Целей пока нет</div>
                        <div class="empty-state-text">Поставьте первую — например, накопить на отпуск</div>
                    </div>
                `;
                return;
            }

            list.innerHTML = goals.map(g => {
                const completed = g.status === 'completed';
                return `
                    <div class="goal-card ${completed ? 'completed' : ''}" data-id="${g.id}">
                        <div class="goal-header">
                            <div class="goal-icon">${g.icon}</div>
                            <div class="goal-title">${ui.escapeHtml(g.title)}</div>
                            ${completed ? '<i class="fas fa-check-circle" style="font-size:20px"></i>' : ''}
                        </div>
                        <div class="goal-progress-bar">
                            <div class="goal-progress-fill" style="width:${Math.min(100, g.progress_percent)}%"></div>
                        </div>
                        <div class="goal-stats">
                            <span>${ui.formatMoney(g.current_amount)} / ${ui.formatMoney(g.target_amount)}</span>
                            <span class="goal-percent">${g.progress_percent.toFixed(0)}%</span>
                        </div>
                        ${g.deadline ? `<div class="category-item-percent">📅 До ${ui.formatDateShort(g.deadline)}</div>` : ''}
                        <div class="goal-actions">
                            ${!completed ? `<button class="btn btn-primary" data-action="contribute" data-id="${g.id}">
                                <i class="fas fa-plus"></i> Пополнить
                            </button>` : ''}
                            <button class="btn btn-secondary" data-action="edit" data-id="${g.id}">
                                <i class="fas fa-edit"></i>
                            </button>
                        </div>
                    </div>
                `;
            }).join('');

            // События
            list.querySelectorAll('[data-action="contribute"]').forEach(btn => {
                btn.onclick = (e) => {
                    e.stopPropagation();
                    ui.openContributeModal(Number(btn.dataset.id));
                };
            });
            list.querySelectorAll('[data-action="edit"]').forEach(btn => {
                btn.onclick = async (e) => {
                    e.stopPropagation();
                    const goal = goals.find(x => x.id === Number(btn.dataset.id));
                    if (goal) ui.openGoalModal(goal);
                };
            });
        } catch (e) {
            list.innerHTML = `<div class="empty-state"><i class="fas fa-times-circle"></i><div>${ui.escapeHtml(e.message)}</div></div>`;
        }
    }

    // ===== Инвестиции =====
    async loadInvestments() {
        const list = document.getElementById('investmentsList');
        list.innerHTML = '<div class="skeleton" style="height: 80px;"></div>';

        try {
            const invs = await window.api.listInvestments();
            if (invs.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-chart-line"></i>
                        <div class="empty-state-title">Активов пока нет</div>
                        <div class="empty-state-text">Добавьте свою первую инвестицию</div>
                    </div>
                `;
                return;
            }

            list.innerHTML = invs.map(i => {
                const plClass = i.profit_loss > 0 ? 'positive' : (i.profit_loss < 0 ? 'negative' : '');
                const plSign = i.profit_loss > 0 ? '+' : '';
                const typeLabel = {
                    stock: '📈 Акции',
                    bond: '📜 Облигация',
                    crypto: '₿ Крипта',
                    deposit: '🏦 Депозит',
                    real_estate: '🏠 Недвижимость',
                    other: '💎 Другое',
                }[i.type] || i.type;

                return `
                    <div class="investment-card" data-id="${i.id}">
                        <div class="investment-header">
                            <div>
                                <span class="investment-name">${ui.escapeHtml(i.name)}</span>
                                ${i.ticker ? `<span class="investment-ticker">${ui.escapeHtml(i.ticker)}</span>` : ''}
                            </div>
                        </div>
                        <div class="investment-amount">${ui.formatMoney(i.current_value || i.purchase_amount)}</div>
                        <div class="investment-meta">${typeLabel} • вложено ${ui.formatMoney(i.purchase_amount)} • с ${ui.formatDateShort(i.purchase_date)}</div>
                        ${plClass ? `<div class="investment-pl ${plClass}">${plSign}${ui.formatMoney(i.profit_loss)} (${i.profit_loss_percent.toFixed(2)}%)</div>` : ''}
                    </div>
                `;
            }).join('');

            list.querySelectorAll('.investment-card').forEach(card => {
                card.onclick = () => {
                    const inv = invs.find(x => x.id === Number(card.dataset.id));
                    if (inv) ui.openInvestmentModal(inv);
                };
            });
        } catch (e) {
            list.innerHTML = `<div class="empty-state"><i class="fas fa-times-circle"></i><div>${ui.escapeHtml(e.message)}</div></div>`;
        }
    }

    // ===== Реферальная статистика =====
    async loadReferralStats() {
        try {
            const stats = await window.api.referralStats();
            document.getElementById('refTotal').textContent = stats.total_referred;
            document.getElementById('refConfirmed').textContent = stats.confirmed_referred;
        } catch (e) {
            console.error('Не удалось загрузить статистику рефералов:', e);
        }
    }

    // ===== Биндинг событий =====
    bindEvents() {
        // Нижняя навигация
        document.querySelectorAll('.nav-item').forEach(item => {
            item.onclick = () => ui.switchPage(item.dataset.nav);
        });

        // Загрузка данных при переходе на страницу
        document.addEventListener('page:change', (e) => {
            const { name } = e.detail;
            if (name === 'transactions') this.loadTransactions(true);
            else if (name === 'goals') this.loadGoals();
            else if (name === 'investments') this.loadInvestments();
            else if (name === 'profile') this.loadReferralStats();
            else if (name === 'dashboard') {
                window.api.dashboard().then(d => this.renderDashboard(d)).catch(() => {});
            }
        });

        // Toggle balance visibility
        document.getElementById('toggleBalance').onclick = () => {
            this.balanceVisible = !this.balanceVisible;
            document.getElementById('balanceAmount').classList.toggle('hidden', !this.balanceVisible);
            document.querySelectorAll('.balance-stat-value').forEach(el => {
                el.style.filter = this.balanceVisible ? '' : 'blur(8px)';
            });
        };

        // Refresh advice
        document.getElementById('refreshAdvice').onclick = async () => {
            const body = document.getElementById('adviceBody');
            body.innerHTML = '<div class="skeleton" style="height: 60px;"></div>';
            try {
                const advice = await window.api.advice();
                this.renderAdvice(advice);
            } catch {
                this.renderAdviceError();
            }
        };

        // Форматирование сумм по мере ввода
        document.querySelectorAll('.amount-input').forEach(input => {
            input.oninput = () => ui.formatCurrencyInput(input);
        });

        // === Транзакция: submit ===
        document.getElementById('txSubmit').onclick = async () => {
            const amount = ui.parseAmount(document.getElementById('txAmount').value);
            if (!amount || amount <= 0) {
                ui.showToast('Введите корректную сумму', 'warning');
                return;
            }
            const kind = document.getElementById('txKind').value;
            const categoryId = document.getElementById('txCategoryId').value;
            const description = document.getElementById('txDescription').value.trim();
            const occurredAt = document.getElementById('txDate').value;
            const editId = document.getElementById('txEditId').value;

            const payload = {
                kind,
                amount: String(amount),
                category_id: categoryId ? Number(categoryId) : null,
                description: description || null,
                occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
            };

            try {
                if (editId) {
                    await window.api.updateTransaction(Number(editId), payload);
                    ui.showToast('Транзакция обновлена', 'success');
                } else {
                    await window.api.createTransaction(payload);
                    ui.showToast(kind === 'income' ? 'Доход добавлен 🎉' : 'Расход добавлен', 'success');
                }
                ui.closeModal('txModal');
                await this.refreshAfterChange();
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        document.getElementById('txDelete').onclick = async () => {
            const id = document.getElementById('txEditId').value;
            if (!id) return;
            if (!confirm('Удалить транзакцию?')) return;
            try {
                await window.api.deleteTransaction(Number(id));
                ui.showToast('Удалено', 'success');
                ui.closeModal('txModal');
                await this.refreshAfterChange();
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        // === Цель: submit ===
        document.querySelectorAll('.emoji-btn').forEach(btn => {
            btn.onclick = () => {
                document.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('goalIcon').value = btn.dataset.emoji;
                ui.haptic('light');
            };
        });

        document.getElementById('goalSubmit').onclick = async () => {
            const title = document.getElementById('goalTitle').value.trim();
            const target = ui.parseAmount(document.getElementById('goalTargetAmount').value);
            const current = ui.parseAmount(document.getElementById('goalCurrentAmount').value);
            const deadline = document.getElementById('goalDeadline').value || null;
            const icon = document.getElementById('goalIcon').value;
            const editId = document.getElementById('goalEditId').value;

            if (!title) { ui.showToast('Введите название', 'warning'); return; }
            if (!target || target <= 0) { ui.showToast('Введите целевую сумму', 'warning'); return; }

            const payload = {
                title,
                target_amount: String(target),
                current_amount: String(current || 0),
                deadline,
                icon,
            };

            try {
                if (editId) {
                    await window.api.updateGoal(Number(editId), payload);
                    ui.showToast('Цель обновлена', 'success');
                } else {
                    await window.api.createGoal(payload);
                    ui.showToast('Цель создана 🎯', 'success');
                }
                ui.closeModal('goalModal');
                if (ui.currentPage === 'goals') await this.loadGoals();
                if (ui.currentPage === 'dashboard') {
                    const d = await window.api.dashboard();
                    this.renderDashboard(d);
                }
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        document.getElementById('goalDelete').onclick = async () => {
            const id = document.getElementById('goalEditId').value;
            if (!id || !confirm('Удалить цель?')) return;
            try {
                await window.api.deleteGoal(Number(id));
                ui.showToast('Удалено', 'success');
                ui.closeModal('goalModal');
                await this.loadGoals();
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        // === Пополнение цели ===
        document.getElementById('contributeSubmit').onclick = async () => {
            const id = document.getElementById('contributeGoalId').value;
            const amount = ui.parseAmount(document.getElementById('contributeAmount').value);
            if (!amount || amount <= 0) { ui.showToast('Введите сумму', 'warning'); return; }
            try {
                await window.api.contributeToGoal(Number(id), amount);
                ui.showToast(`Цель пополнена на ${ui.formatMoney(amount)} 💪`, 'success');
                ui.closeModal('contributeModal');
                await this.loadGoals();
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        // === Инвестиция: submit ===
        document.getElementById('investmentSubmit').onclick = async () => {
            const type = document.getElementById('investmentType').value;
            const name = document.getElementById('investmentName').value.trim();
            const ticker = document.getElementById('investmentTicker').value.trim() || null;
            const amount = ui.parseAmount(document.getElementById('investmentAmount').value);
            const date = document.getElementById('investmentDate').value;
            const editId = document.getElementById('investmentEditId').value;

            if (!name) { ui.showToast('Введите название', 'warning'); return; }
            if (!amount || amount <= 0) { ui.showToast('Введите сумму', 'warning'); return; }
            if (!date) { ui.showToast('Укажите дату покупки', 'warning'); return; }

            const payload = {
                type,
                name,
                ticker,
                purchase_amount: String(amount),
                purchase_date: date,
            };

            try {
                if (editId) {
                    await window.api.updateInvestment(Number(editId), { name, ticker });
                    ui.showToast('Инвестиция обновлена', 'success');
                } else {
                    await window.api.createInvestment(payload);
                    ui.showToast('Инвестиция добавлена 📈', 'success');
                }
                ui.closeModal('investmentModal');
                await this.loadInvestments();
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        document.getElementById('investmentDelete').onclick = async () => {
            const id = document.getElementById('investmentEditId').value;
            if (!id || !confirm('Удалить инвестицию?')) return;
            try {
                await window.api.deleteInvestment(Number(id));
                ui.showToast('Удалено', 'success');
                ui.closeModal('investmentModal');
                await this.loadInvestments();
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        // === Фильтры транзакций ===
        document.querySelectorAll('[data-filter-kind]').forEach(btn => {
            btn.onclick = () => {
                document.querySelectorAll('[data-filter-kind]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.txFilter.kind = btn.dataset.filterKind;
                this.loadTransactions(true);
            };
        });

        let searchTimer;
        document.getElementById('searchInput').oninput = (e) => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                this.txFilter.search = e.target.value.trim();
                this.loadTransactions(true);
            }, 400);
        };

        document.getElementById('loadMoreBtn').onclick = () => {
            this.txFilter.page += 1;
            this.loadTransactions(false);
        };

        // === Реферальная программа ===
        document.getElementById('copyReferralBtn').onclick = async () => {
            const code = document.getElementById('referralCode').textContent;
            try {
                await navigator.clipboard.writeText(code);
                ui.showToast('Код скопирован', 'success');
            } catch {
                ui.showToast('Не удалось скопировать', 'error');
            }
        };

        document.getElementById('shareReferralBtn').onclick = async () => {
            try {
                const stats = await window.api.referralStats();
                const url = stats.referral_url;
                if (this.tg?.openTelegramLink && url) {
                    this.tg.openTelegramLink(url);
                } else if (navigator.share) {
                    await navigator.share({
                        title: 'Финансовый Трекер',
                        text: `Присоединяйся к Финансовому Трекеру по моей ссылке! Код: ${stats.referral_code}`,
                        url: url,
                    });
                } else {
                    await navigator.clipboard.writeText(url);
                    ui.showToast('Ссылка скопирована', 'success');
                }
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        // === Экспорт ===
        document.getElementById('exportCsvBtn').onclick = async () => {
            try {
                ui.showToast('Готовим экспорт...', 'info');
                await window.api.downloadExport('csv');
                ui.showToast('Файл сохранён', 'success');
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        document.getElementById('exportJsonBtn').onclick = async () => {
            try {
                ui.showToast('Готовим экспорт...', 'info');
                await window.api.downloadExport('json');
                ui.showToast('Файл сохранён', 'success');
            } catch (e) {
                ui.showToast(e.message, 'error');
            }
        };

        // BackButton от Telegram — закрывает модалку или возвращает на главную
        if (this.tg?.BackButton) {
            this.tg.BackButton.onClick(() => {
                if (ui.modalStack.length > 0) {
                    ui.closeModal(ui.modalStack[ui.modalStack.length - 1]);
                } else if (ui.currentPage !== 'dashboard') {
                    ui.switchPage('dashboard');
                }
            });
            // Показываем кнопку Back, когда не на главной или открыта модалка
            const updateBackButton = () => {
                if (ui.currentPage !== 'dashboard' || ui.modalStack.length > 0) {
                    this.tg.BackButton.show();
                } else {
                    this.tg.BackButton.hide();
                }
            };
            document.addEventListener('page:change', updateBackButton);
            updateBackButton();
        }
    }

    async refreshAfterChange() {
        // Обновляем дашборд независимо от текущей страницы
        try {
            const d = await window.api.dashboard();
            this.renderDashboard(d);
            const advice = await window.api.advice();
            this.renderAdvice(advice);
        } catch {}

        if (ui.currentPage === 'transactions') {
            await this.loadTransactions(true);
        }
    }
}

// Старт приложения после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    window.app.init();
});
