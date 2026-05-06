/**
 * API клиент для финансового трекера.
 * - Автоматически передаёт Authorization: Bearer <access_token>
 * - При 401 пробует обновить токен через refresh
 * - Хранит токены в Telegram CloudStorage (или localStorage как fallback)
 */

const API_BASE = (() => {
    // По умолчанию — относительный путь, но если фронт хостится отдельно
    // (GitHub Pages), нужно задать абсолютный URL backend'а.
    // Можно переопределить через ?api=https://my-backend.com в URL.
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get('api');
    if (fromUrl) return fromUrl.replace(/\/$/, '');

    // Если index.html лежит на том же домене, что и API — используем относительный путь
    if (window.API_BASE_URL) return window.API_BASE_URL.replace(/\/$/, '');

    // Иначе — пытаемся угадать
    const meta = document.querySelector('meta[name="api-base"]');
    if (meta) return meta.content.replace(/\/$/, '');

    return ''; // относительный
})();

class TokenStorage {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.useCloud = this.tg?.CloudStorage && this.tg?.isVersionAtLeast?.('6.9');
    }

    async get(key) {
        if (this.useCloud) {
            return new Promise((resolve) => {
                this.tg.CloudStorage.getItem(key, (err, value) => {
                    if (err || !value) resolve(localStorage.getItem(key));
                    else resolve(value);
                });
            });
        }
        return localStorage.getItem(key);
    }

    async set(key, value) {
        // Дублируем в обоих местах для надёжности
        localStorage.setItem(key, value);
        if (this.useCloud) {
            return new Promise((resolve) => {
                this.tg.CloudStorage.setItem(key, value, () => resolve());
            });
        }
    }

    async remove(key) {
        localStorage.removeItem(key);
        if (this.useCloud) {
            return new Promise((resolve) => {
                this.tg.CloudStorage.removeItem(key, () => resolve());
            });
        }
    }
}

class API {
    constructor() {
        this.base = API_BASE;
        this.storage = new TokenStorage();
        this.accessToken = null;
        this.refreshToken = null;
        this.user = null;
    }

    async init() {
        this.accessToken = await this.storage.get('access_token');
        this.refreshToken = await this.storage.get('refresh_token');
    }

    async authenticate() {
        const tg = window.Telegram?.WebApp;
        const initData = tg?.initData;
        if (!initData) {
            throw new Error('Это приложение должно запускаться в Telegram.');
        }

        const res = await fetch(`${this.base}/api/v1/auth/telegram`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ init_data: initData }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Ошибка авторизации: ${res.status}`);
        }

        const data = await res.json();
        this.accessToken = data.access_token;
        this.refreshToken = data.refresh_token;
        this.user = data.user;

        await this.storage.set('access_token', this.accessToken);
        await this.storage.set('refresh_token', this.refreshToken);

        return this.user;
    }

    async refreshAccess() {
        if (!this.refreshToken) return false;
        try {
            const res = await fetch(`${this.base}/api/v1/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.refreshToken }),
            });
            if (!res.ok) return false;
            const data = await res.json();
            this.accessToken = data.access_token;
            await this.storage.set('access_token', this.accessToken);
            return true;
        } catch {
            return false;
        }
    }

    async _fetch(path, options = {}) {
        const url = `${this.base}${path}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (this.accessToken) {
            headers.Authorization = `Bearer ${this.accessToken}`;
        }

        let res = await fetch(url, { ...options, headers });

        // Попытка обновить токен и повторить
        if (res.status === 401 && this.refreshToken) {
            const ok = await this.refreshAccess();
            if (ok) {
                headers.Authorization = `Bearer ${this.accessToken}`;
                res = await fetch(url, { ...options, headers });
            } else {
                // Не получилось — нужна полная переавторизация
                await this.authenticate();
                headers.Authorization = `Bearer ${this.accessToken}`;
                res = await fetch(url, { ...options, headers });
            }
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            const error = new Error(err.detail || `HTTP ${res.status}`);
            error.status = res.status;
            throw error;
        }

        if (res.status === 204) return null;

        const ct = res.headers.get('Content-Type') || '';
        if (ct.includes('application/json')) return res.json();
        return res;
    }

    // === Endpoints ===

    // Users
    me() { return this._fetch('/api/v1/users/me'); }
    updateMe(data) { return this._fetch('/api/v1/users/me', { method: 'PATCH', body: JSON.stringify(data) }); }

    // Transactions
    listTransactions(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') query.set(k, v);
        });
        return this._fetch(`/api/v1/transactions?${query}`);
    }
    createTransaction(data) {
        return this._fetch('/api/v1/transactions', { method: 'POST', body: JSON.stringify(data) });
    }
    updateTransaction(id, data) {
        return this._fetch(`/api/v1/transactions/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
    }
    deleteTransaction(id) {
        return this._fetch(`/api/v1/transactions/${id}`, { method: 'DELETE' });
    }

    // Categories
    listCategories(kind) {
        const q = kind ? `?kind=${kind}` : '';
        return this._fetch(`/api/v1/categories${q}`);
    }
    createCategory(data) {
        return this._fetch('/api/v1/categories', { method: 'POST', body: JSON.stringify(data) });
    }
    deleteCategory(id) {
        return this._fetch(`/api/v1/categories/${id}`, { method: 'DELETE' });
    }

    // Goals
    listGoals(status) {
        const q = status ? `?status_filter=${status}` : '';
        return this._fetch(`/api/v1/goals${q}`);
    }
    createGoal(data) {
        return this._fetch('/api/v1/goals', { method: 'POST', body: JSON.stringify(data) });
    }
    updateGoal(id, data) {
        return this._fetch(`/api/v1/goals/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
    }
    contributeToGoal(id, amount, comment) {
        return this._fetch(`/api/v1/goals/${id}/contribute`, {
            method: 'POST',
            body: JSON.stringify({ amount: String(amount), comment: comment || null }),
        });
    }
    deleteGoal(id) {
        return this._fetch(`/api/v1/goals/${id}`, { method: 'DELETE' });
    }

    // Investments
    listInvestments() { return this._fetch('/api/v1/investments'); }
    createInvestment(data) {
        return this._fetch('/api/v1/investments', { method: 'POST', body: JSON.stringify(data) });
    }
    updateInvestment(id, data) {
        return this._fetch(`/api/v1/investments/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
    }
    deleteInvestment(id) {
        return this._fetch(`/api/v1/investments/${id}`, { method: 'DELETE' });
    }

    // Analytics
    dashboard() { return this._fetch('/api/v1/analytics/dashboard'); }
    period(start, end) {
        return this._fetch(`/api/v1/analytics/period?start=${start}&end=${end}`);
    }
    trend(days = 30) { return this._fetch(`/api/v1/analytics/trend?days=${days}`); }
    advice() { return this._fetch('/api/v1/analytics/advice'); }

    // Referrals
    referralStats() { return this._fetch('/api/v1/referrals/me'); }

    // Export — возвращает Response для скачивания
    exportCsvUrl() { return `${this.base}/api/v1/export/transactions.csv`; }
    exportJsonUrl() { return `${this.base}/api/v1/export/full.json`; }

    async downloadExport(format) {
        const url = format === 'csv' ? this.exportCsvUrl() : this.exportJsonUrl();
        const res = await fetch(url, {
            headers: { Authorization: `Bearer ${this.accessToken}` },
        });
        if (!res.ok) throw new Error('Не удалось скачать экспорт');
        const blob = await res.blob();
        const cd = res.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename="?([^";]+)"?/);
        const filename = match ? match[1] : `export.${format}`;
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(a.href);
    }
}

window.api = new API();
