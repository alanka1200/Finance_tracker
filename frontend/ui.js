/**
 * UI слой: модалки, форматтеры, навигация, тосты.
 * Использует Telegram WebApp API для тактильной обратной связи.
 */

class UI {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.currentPage = 'dashboard';
        this.modalStack = [];
    }

    // ===== Хаптики =====
    haptic(type = 'light') {
        try {
            if (type === 'success' || type === 'warning' || type === 'error') {
                this.tg?.HapticFeedback?.notificationOccurred(type);
            } else {
                this.tg?.HapticFeedback?.impactOccurred(type); // light, medium, heavy, soft, rigid
            }
        } catch {}
    }

    // ===== Форматтеры =====
    formatMoney(amount, currency = 'RUB') {
        const n = Number(amount) || 0;
        const symbol = { RUB: '₽', USD: '$', EUR: '€', BTC: '₿' }[currency] || currency;
        // Тысячи через тонкий пробел, без копеек если они нулевые
        const isInt = Math.abs(n - Math.round(n)) < 0.005;
        const formatted = isInt
            ? Math.round(n).toLocaleString('ru-RU')
            : n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return `${formatted} ${symbol}`;
    }

    formatDate(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        const today = new Date();
        const yesterday = new Date(Date.now() - 86400000);

        const isSameDay = (a, b) =>
            a.getFullYear() === b.getFullYear() &&
            a.getMonth() === b.getMonth() &&
            a.getDate() === b.getDate();

        const time = d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

        if (isSameDay(d, today)) return `сегодня, ${time}`;
        if (isSameDay(d, yesterday)) return `вчера, ${time}`;

        return d.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    formatDateShort(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    }

    /**
     * Форматирует число в input по мере ввода: "12345" → "12 345".
     * Сохраняет позицию каретки.
     */
    formatCurrencyInput(input) {
        const cursorPos = input.selectionStart;
        const oldVal = input.value;
        const cleaned = oldVal.replace(/\s/g, '').replace(/[^\d.,]/g, '').replace(',', '.');

        if (!cleaned) {
            input.value = '';
            return;
        }

        const parts = cleaned.split('.');
        const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
        const formatted = parts.length > 1
            ? `${intPart}.${parts[1].slice(0, 4)}`
            : intPart;

        input.value = formatted;

        // Возвращаем каретку
        const diff = formatted.length - oldVal.length;
        try {
            input.setSelectionRange(cursorPos + diff, cursorPos + diff);
        } catch {}
    }

    parseAmount(str) {
        if (!str) return 0;
        return parseFloat(String(str).replace(/\s/g, '').replace(',', '.')) || 0;
    }

    // ===== Toast =====
    showToast(text, type = 'info', duration = 3000) {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icon = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle',
        }[type] || 'fa-info-circle';
        toast.innerHTML = `<i class="fas ${icon}"></i><span>${this.escapeHtml(text)}</span>`;
        container.appendChild(toast);

        if (type === 'success') this.haptic('success');
        else if (type === 'error') this.haptic('error');
        else if (type === 'warning') this.haptic('warning');

        setTimeout(() => toast.remove(), duration);
    }

    escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = String(s ?? '');
        return div.innerHTML;
    }

    // ===== Навигация =====
    switchPage(name) {
        if (this.currentPage === name) return;

        document.querySelectorAll('.page').forEach(el => {
            el.hidden = el.dataset.page !== name;
        });
        document.querySelectorAll('.nav-item').forEach(el => {
            el.classList.toggle('active', el.dataset.nav === name);
        });

        this.currentPage = name;
        this.haptic('light');

        // Прокрутка наверх при переходе
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Триггерим перезагрузку данных страницы
        document.dispatchEvent(new CustomEvent('page:change', { detail: { name } }));
    }

    // ===== Модалки =====
    openModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.add('show');
        this.modalStack.push(id);
        document.body.style.overflow = 'hidden';
        this.haptic('light');

        // Закрытие по клику на фон
        modal.onclick = (e) => {
            if (e.target === modal) this.closeModal(id);
        };
    }

    closeModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.remove('show');
        this.modalStack = this.modalStack.filter(x => x !== id);
        if (this.modalStack.length === 0) {
            document.body.style.overflow = '';
        }
    }

    closeAllModals() {
        document.querySelectorAll('.modal').forEach(m => m.classList.remove('show'));
        this.modalStack = [];
        document.body.style.overflow = '';
    }

    // ===== Открытие конкретных модалок =====
    async openTxModal(kind, txData = null) {
        document.getElementById('txKind').value = kind;
        document.getElementById('txEditId').value = txData?.id || '';

        const title = txData
            ? '<i class="fas fa-edit"></i> Редактировать'
            : (kind === 'income' ? '<i class="fas fa-plus"></i> Новый доход' : '<i class="fas fa-minus"></i> Новый расход');
        document.getElementById('txModalTitle').innerHTML = title;

        const submitBtn = document.getElementById('txSubmit');
        submitBtn.innerHTML = txData
            ? '<i class="fas fa-save"></i> Сохранить'
            : '<i class="fas fa-check"></i> Добавить';

        document.getElementById('txDelete').hidden = !txData;

        // Заполняем поля
        document.getElementById('txAmount').value = txData ? this.formatCurrencyInputValue(txData.amount) : '';
        document.getElementById('txDescription').value = txData?.description || '';
        document.getElementById('txDate').value = this.toLocalDateTime(txData?.occurred_at || new Date());
        document.getElementById('txCategoryId').value = txData?.category_id || '';

        // Загружаем категории
        await this.renderCategoryGrid(kind, txData?.category_id);

        this.openModal('txModal');
        setTimeout(() => document.getElementById('txAmount')?.focus(), 300);
    }

    async renderCategoryGrid(kind, selectedId = null) {
        const grid = document.getElementById('txCategoryGrid');
        grid.innerHTML = '<div class="skeleton" style="height: 80px; grid-column: 1 / -1;"></div>';
        try {
            const cats = await window.api.listCategories(kind);
            grid.innerHTML = '';
            for (const cat of cats) {
                const chip = document.createElement('div');
                chip.className = 'category-chip';
                if (cat.id === Number(selectedId)) chip.classList.add('active');
                chip.dataset.id = cat.id;
                chip.innerHTML = `
                    <div class="category-chip-icon" style="background:${cat.color}">${cat.icon}</div>
                    <div class="category-chip-name">${this.escapeHtml(cat.name)}</div>
                `;
                chip.onclick = () => {
                    grid.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    document.getElementById('txCategoryId').value = cat.id;
                    this.haptic('light');
                };
                grid.appendChild(chip);
            }
            // Авто-выбор первой категории если ничего не выбрано
            if (!selectedId && cats.length > 0) {
                grid.querySelector('.category-chip')?.classList.add('active');
                document.getElementById('txCategoryId').value = cats[0].id;
            }
        } catch (e) {
            grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><i class="fas fa-folder-open"></i><div>Не удалось загрузить категории</div></div>`;
        }
    }

    openGoalModal(goalData = null) {
        document.getElementById('goalEditId').value = goalData?.id || '';
        document.getElementById('goalModalTitle').innerHTML = goalData
            ? '<i class="fas fa-edit"></i> Редактировать цель'
            : '<i class="fas fa-bullseye"></i> Новая цель';

        document.getElementById('goalSubmit').innerHTML = goalData
            ? '<i class="fas fa-save"></i> Сохранить'
            : '<i class="fas fa-check"></i> Создать';
        document.getElementById('goalDelete').hidden = !goalData;

        document.getElementById('goalTitle').value = goalData?.title || '';
        document.getElementById('goalTargetAmount').value = goalData ? this.formatCurrencyInputValue(goalData.target_amount) : '';
        document.getElementById('goalCurrentAmount').value = goalData ? this.formatCurrencyInputValue(goalData.current_amount) : '';
        document.getElementById('goalDeadline').value = goalData?.deadline || '';
        document.getElementById('goalIcon').value = goalData?.icon || '🎯';

        // Активная иконка
        document.querySelectorAll('.emoji-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.emoji === (goalData?.icon || '🎯'));
        });

        this.openModal('goalModal');
        setTimeout(() => document.getElementById('goalTitle')?.focus(), 300);
    }

    openContributeModal(goalId) {
        document.getElementById('contributeGoalId').value = goalId;
        document.getElementById('contributeAmount').value = '';
        this.openModal('contributeModal');
        setTimeout(() => document.getElementById('contributeAmount')?.focus(), 300);
    }

    openInvestmentModal(invData = null) {
        document.getElementById('investmentEditId').value = invData?.id || '';
        document.getElementById('investmentModalTitle').innerHTML = invData
            ? '<i class="fas fa-edit"></i> Редактировать инвестицию'
            : '<i class="fas fa-chart-line"></i> Новая инвестиция';

        document.getElementById('investmentSubmit').innerHTML = invData
            ? '<i class="fas fa-save"></i> Сохранить'
            : '<i class="fas fa-check"></i> Добавить';
        document.getElementById('investmentDelete').hidden = !invData;

        document.getElementById('investmentType').value = invData?.type || 'stock';
        document.getElementById('investmentName').value = invData?.name || '';
        document.getElementById('investmentTicker').value = invData?.ticker || '';
        document.getElementById('investmentAmount').value = invData ? this.formatCurrencyInputValue(invData.purchase_amount) : '';
        document.getElementById('investmentDate').value = invData?.purchase_date || new Date().toISOString().slice(0, 10);

        this.openModal('investmentModal');
    }

    formatCurrencyInputValue(amount) {
        const n = Number(amount) || 0;
        return n.toLocaleString('ru-RU').replace(/,/g, ' ');
    }

    toLocalDateTime(d) {
        const date = typeof d === 'string' ? new Date(d) : d;
        // datetime-local формат: YYYY-MM-DDTHH:mm
        const offset = date.getTimezoneOffset() * 60000;
        return new Date(date.getTime() - offset).toISOString().slice(0, 16);
    }

    setCurrentDate() {
        const el = document.getElementById('currentDate');
        if (el) {
            el.textContent = new Date().toLocaleDateString('ru-RU', {
                day: 'numeric', month: 'long', weekday: 'short',
            });
        }
    }
}

window.ui = new UI();
