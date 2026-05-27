/**
 * Toast-уведомления
 * 
 * Использование:
 *   toast.success('Операция успешна!');
 *   toast.error('Произошла ошибка');
 *   toast.warning('Внимание!');
 *   toast.info('Информация');
 * 
 * Или из cookie (flash-сообщения):
 *   Toast.showFromCookie();
 */

const Toast = (function() {
    'use strict';

    // Конфигурация
    const config = {
        duration: 5000,      // Время отображения (мс)
        maxToasts: 5,        // Максимум одновременно
        position: 'top-right'
    };

    // Счётчик для ID
    let idCounter = 0;

    // Список активных toast
    const activeToasts = [];

    // Получить или создать контейнер
    function getContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }

    // Создать toast элемент
    function createToastElement(options) {
        const id = `toast-${++idCounter}`;
        
        const toast = document.createElement('div');
        toast.id = id;
        toast.className = `toast toast--${options.type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        // Иконки
        const icons = {
            success: 'check_circle',
            error: 'error',
            warning: 'warning',
            info: 'info'
        };

        toast.innerHTML = `
            <div class="toast__icon">
                <span class="material-icons">${icons[options.type]}</span>
            </div>
            <div class="toast__content">
                ${options.title ? `<div class="toast__title">${options.title}</div>` : ''}
                <div class="toast__message">${options.message}</div>
            </div>
            <button class="toast__close" aria-label="Закрыть">
                <span class="material-icons">close</span>
            </button>
            <div class="toast__progress"></div>
        `;

        return { element: toast, id };
    }

    // Показать toast
    function show(options) {
        const container = getContainer();

        // Удалить старые toast, если превышен лимит
        while (activeToasts.length >= config.maxToasts) {
            remove(activeToasts[0].id);
        }

        // Создать элемент
        const { element, id } = createToastElement(options);
        container.appendChild(element);

        // Добавить в список активных
        const toastData = { id, element, timeout: null };
        activeToasts.push(toastData);

        // Закрытие по клику
        const closeBtn = element.querySelector('.toast__close');
        closeBtn.addEventListener('click', () => remove(id));

        // Авто-закрытие
        const duration = options.duration || config.duration;
        if (duration > 0) {
            toastData.timeout = setTimeout(() => remove(id), duration);
        }

        return id;
    }

    // Удалить toast
    function remove(id) {
        const index = activeToasts.findIndex(t => t.id === id);
        if (index === -1) return;

        const toast = activeToasts[index];

        // Отменить таймер
        if (toast.timeout) {
            clearTimeout(toast.timeout);
        }

        // Анимация закрытия
        toast.element.classList.add('hiding');

        // Удалить из DOM
        setTimeout(() => {
            if (toast.element.parentNode) {
                toast.element.parentNode.removeChild(toast.element);
            }
        }, 300);

        // Удалить из списка
        activeToasts.splice(index, 1);
    }

    // Получить flash-сообщение из cookie и показать
    function showFromCookie() {
        const cookies = document.cookie.split(';');
        let flashData = null;

        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'flash_message' && value) {
                try {
                    flashData = JSON.parse(decodeURIComponent(value));
                } catch (e) {
                    console.error('Ошибка парсинга flash-сообщения:', e);
                }
                break;
            }
        }

        if (flashData) {
            // Показать toast
            show({
                type: flashData.type || 'info',
                message: flashData.message,
                duration: 5000
            });

            // Очистить cookie
            document.cookie = 'flash_message=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        }
    }

    // Публичный API
    return {
        show,
        success: (message, options = {}) => show({ type: 'success', message, ...options }),
        error: (message, options = {}) => show({ type: 'error', message, ...options }),
        warning: (message, options = {}) => show({ type: 'warning', message, ...options }),
        info: (message, options = {}) => show({ type: 'info', message, ...options }),
        remove,
        showFromCookie
    };
})();

// Глобальная функция для удобства
const toast = Toast;

// Автоматическая инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
    // Показать flash-сообщения из cookie
    Toast.showFromCookie();
});
