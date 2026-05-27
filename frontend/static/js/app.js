/**
 * Основной JavaScript файл для фронтенда системы парковки.
 * Инициализация Alpine.js, обработка HTMX событий, работа с cookie.
 */

// ===== ИНИЦИАЛИЗАЦИЯ ALPINE =====
document.addEventListener('alpine:init', () => {
    console.log('Alpine.js инициализирован');

    // Глобальные данные
    Alpine.store('app', {
        user: null,
        token: null,
        darkMode: window.matchMedia('(prefers-color-scheme: dark)').matches,

        init() {
            this.loadUser();
            this.loadToken();
        },

        loadUser() {
            // Попытка получить данные пользователя из cookie/localStorage
            const userData = localStorage.getItem('parking_user');
            if (userData) {
                try {
                    this.user = JSON.parse(userData);
                } catch (e) {
                    console.warn('Не удалось распарсить данные пользователя', e);
                }
            }
        },

        loadToken() {
            // Токен хранится в httpOnly cookie, поэтому на клиенте мы его не читаем.
            // Но можем проверить наличие cookie с именем 'access_token'.
            this.token = document.cookie.includes('access_token') ? 'present' : null;
        },

        toggleDarkMode() {
            this.darkMode = !this.darkMode;
            document.documentElement.classList.toggle('dark', this.darkMode);
            localStorage.setItem('parking_dark_mode', this.darkMode);
        }
    });

    // Глобальные утилиты
    Alpine.data('utils', () => ({
        formatDateTime(isoString) {
            if (!isoString) return '—';
            const date = new Date(isoString);
            return date.toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        formatTime(isoString) {
            if (!isoString) return '—';
            const date = new Date(isoString);
            return date.toLocaleTimeString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        formatCurrency(amount) {
            if (amount === null || amount === undefined) return '0 ₽';
            return `${parseFloat(amount).toFixed(2)} ₽`;
        },

        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    }));
});

// ===== ОБРАБОТКА HTMX СОБЫТИЙ =====

// Показать/скрыть индикатор загрузки
document.addEventListener('htmx:beforeRequest', (event) => {
    const target = event.detail.target;
    if (target) {
        target.classList.add('htmx-request');
    }
});

document.addEventListener('htmx:afterRequest', (event) => {
    const target = event.detail.target;
    if (target) {
        target.classList.remove('htmx-request');
    }
});

// Глобальная обработка успешных ответов (редиректы, уведомления)
document.addEventListener('htmx:afterRequest', (event) => {
    const xhr = event.detail.xhr;
    const path = event.detail.requestConfig?.path;

    // Автоматический редирект при успешной авторизации
    if (path === '/api/auth/login' && xhr.status === 200) {
        console.log('Вход успешен, редирект на /dashboard');
        // Редирект уже выполняется в login.html, но на всякий случай дублируем
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 800);
        return;
    }

    // Обработка выхода
    if (path === '/auth/logout' && xhr.status === 200) {
        console.log('Выход выполнен, редирект на /');
        window.location.href = '/';
        return;
    }

    // Показать toast при успешных операциях (кроме тех, что уже обработаны)
    if (xhr.status >= 200 && xhr.status < 300) {
        const contentType = xhr.getResponseHeader('content-type');
        if (contentType && contentType.includes('application/json')) {
            try {
                const data = JSON.parse(xhr.responseText);
                if (data.message && !path?.includes('/api/sessions/history')) {
                    showToast(data.message, 'success');
                }
            } catch (e) {
                // Не JSON ответ
            }
        }
    }

    // Обработка ошибок 4xx/5xx
    if (xhr.status >= 400) {
        let message = `Ошибка ${xhr.status}`;
        try {
            const data = JSON.parse(xhr.responseText);
            if (data.detail) {
                message = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(', ') : data.detail;
            } else if (data.message) {
                message = data.message;
            }
        } catch (e) {
            message = xhr.responseText || 'Неизвестная ошибка';
        }
        showToast(message, 'error');
    }
});

// ===== РАБОТА С COOKIE =====
/**
 * Получить значение cookie по имени.
 * @param {string} name - Имя cookie.
 * @returns {string|null} Значение cookie или null.
 */
function getCookie(name) {
    const matches = document.cookie.match(new RegExp(
        '(?:^|; )' + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + '=([^;]*)'
    ));
    return matches ? decodeURIComponent(matches[1]) : null;
}

/**
 * Проверить, авторизован ли пользователь (наличие access_token cookie).
 * @returns {boolean}
 */
function isAuthenticated() {
    return document.cookie.includes('access_token');
}

/**
 * Удалить cookie (используется для выхода).
 * @param {string} name - Имя cookie.
 */
function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

// ===== TOAST УВЕДОМЛЕНИЯ =====
/**
 * Показать всплывающее уведомление.
 * @param {string} text - Текст уведомления.
 * @param {string} type - Тип: 'success', 'error', 'info', 'warning'.
 * @param {number} duration - Длительность показа в миллисекундах.
 */
function showToast(text, type = 'info', duration = 5000) {
    if (typeof Toast !== 'undefined') {
        Toast.show({ message: text, type, duration });
    } else {
        console.warn('Библиотека Toast не найдена, сообщение:', text);
    }
}

// ===== ОБРАБОТЧИКИ СОБЫТИЙ =====

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM загружен, инициализация фронтенда');

    // Применить сохранённую тему
    const savedDarkMode = localStorage.getItem('parking_dark_mode');
    if (savedDarkMode !== null) {
        const isDark = savedDarkMode === 'true';
        document.documentElement.classList.toggle('dark', isDark);
        Alpine.store('app').darkMode = isDark;
    }

    // Проверить авторизацию
    if (!isAuthenticated() && !window.location.pathname.includes('/login') && window.location.pathname !== '/') {
        console.log('Пользователь не авторизован, перенаправление на /');
        // showToast('Требуется авторизация', 'warning');
        // window.location.href = '/';
    }

    // Инициализация Alpine
    if (typeof Alpine === 'undefined') {
        console.error('Alpine.js не загружен');
    }

    // Глобальный обработчик ошибок HTMX
    document.body.addEventListener('htmx:responseError', (event) => {
        console.error('HTMX ошибка:', event.detail);
        showToast('Сетевая ошибка. Проверьте соединение.', 'error');
    });

    // Обработка нажатия на кнопку выхода
    document.querySelectorAll('.logout-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (!confirm('Вы уверены, что хотите выйти?')) {
                e.preventDefault();
            }
        });
    });
});

// ===== ГЛОБАЛЬНЫЕ ФУНКЦИИ ДЛЯ ШАБЛОНОВ =====
window.parkingApp = {
    showToast,
    getCookie,
    deleteCookie,
    isAuthenticated,

    /**
     * Запросить данные с API с обработкой ошибок.
     * @param {string} url - URL endpoint.
     * @param {RequestInit} options - Опции fetch.
     * @returns {Promise<any>} Ответ JSON или null при ошибке.
     */
    async fetchAPI(url, options = {}) {
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Ошибка запроса к ${url}:`, error);
            showToast('Ошибка связи с сервером', 'error');
            return null;
        }
    },

    /**
     * Форматирование длительности в секундах в ЧЧ:ММ:СС.
     * @param {number} seconds - Количество секунд.
     * @returns {string}
     */
    formatDuration(seconds) {
        if (!seconds && seconds !== 0) return '—';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
};

// Экспорт для использования в консоли (отладка)
if (typeof window !== 'undefined') {
    window.Alpine = Alpine;
    window.htmx = htmx;
}