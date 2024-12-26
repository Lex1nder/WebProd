// Общие функции для всех страниц
document.addEventListener('DOMContentLoaded', () => {
    // Плавная прокрутка
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Всплывающие уведомления
    function showNotification(message, type = 'info') {
        const notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'fixed top-4 right-4 z-50';
            document.body.appendChild(container);
        }

        const notification = document.createElement('div');
        notification.className = `
            p-4 mb-4 rounded shadow-lg transition-all duration-300
            ${type === 'success' ? 'bg-green-500 text-white' : 
              type === 'error' ? 'bg-red-500 text-white' : 
              'bg-blue-500 text-white'}
        `;
        notification.textContent = message;

        document.getElementById('notification-container').appendChild(notification);

        // Автоматическое удаление уведомления
        setTimeout(() => {
            notification.classList.add('opacity-0', 'translate-x-full');
            setTimeout(() => {
                notification.remove();
            }, 500);
        }, 3000);
    }

    // Tab switching logic
    const loginTab = document.getElementById('loginTab');
    const registerTab = document.getElementById('registerTab');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const successModal = document.getElementById('successModal');
    const closeSuccessModal = document.getElementById('closeSuccessModal');

    // Debug logging for tab switching
    if (loginTab && registerTab) {
        console.log('Login and Register tabs found');
        loginTab.addEventListener('click', () => {
            console.log('Login tab clicked');
            loginForm.classList.remove('hidden');
            registerForm.classList.add('hidden');
            loginTab.classList.add('border-blue-500', 'text-blue-500');
            loginTab.classList.remove('border-gray-200', 'text-gray-500');
            registerTab.classList.add('border-gray-200', 'text-gray-500');
            registerTab.classList.remove('border-blue-500', 'text-blue-500');
        });

        registerTab.addEventListener('click', () => {
            console.log('Register tab clicked');
            registerForm.classList.remove('hidden');
            loginForm.classList.add('hidden');
            registerTab.classList.add('border-blue-500', 'text-blue-500');
            registerTab.classList.remove('border-gray-200', 'text-gray-500');
            loginTab.classList.add('border-gray-200', 'text-gray-500');
            loginTab.classList.remove('border-blue-500', 'text-blue-500');
        });
    } else {
        console.error('Login or Register tabs not found', {
            loginTab, 
            registerTab, 
            loginForm, 
            registerForm
        });
    }

    // Success modal close
    if (closeSuccessModal && successModal) {
        closeSuccessModal.addEventListener('click', () => {
            successModal.classList.remove('show');
            loginTab.click(); // Switch to login form
        });
    }

    // Login form submission
    const loginFormElement = document.getElementById('loginForm');
    if (loginFormElement) {
        loginFormElement.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password }),
                });

                const data = await response.json();
                if (response.ok) {
                    // Redirect to dashboard or main page
                    window.location.href = '/dashboard';
                } else {
                    showNotification(data.error || 'Ошибка входа', 'error');
                }
            } catch (error) {
                showNotification('Произошла ошибка при входе', 'error');
                console.error('Login error:', error);
            }
        });
    }

    // Register form submission
    const registerFormElement = document.getElementById('registerForm');
    if (registerFormElement) {
        registerFormElement.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('registerUsername').value;
            const email = document.getElementById('registerEmail').value;
            const phone = document.getElementById('registerPhone').value;
            const password = document.getElementById('registerPassword').value;

            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, email, phone, password }),
                });

                const data = await response.json();
                if (response.ok) {
                    // Show success modal
                    if (successModal) {
                        successModal.classList.add('show');
                    }
                    showNotification('Регистрация прошла успешно', 'success');
                } else {
                    showNotification(data.error || 'Ошибка регистрации', 'error');
                }
            } catch (error) {
                showNotification('Произошла ошибка при регистрации', 'error');
                console.error('Registration error:', error);
            }
        });
    }

    // Глобальный обработчик ошибок
    window.addEventListener('error', (event) => {
        showNotification('Произошла непредвиденная ошибка', 'error');
    });

    // Экспорт функций, если нужно использовать глобально
    window.showNotification = showNotification;
});
