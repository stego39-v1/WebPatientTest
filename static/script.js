document.addEventListener('DOMContentLoaded', function() {
    console.log('🏥 Медицинская система загружена');

    // Плавное появление элементов
    document.querySelectorAll('.card, .table-responsive, .chart-container').forEach(el => {
        el.classList.add('fade-in');
    });

    // Подсветка активной навигации
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-right a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.color = 'var(--primary)';
            link.style.borderBottomColor = 'var(--primary-light)';
        }
    });

    // Авто-скрытие алертов через 5 секунд
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Поддержка Enter для отправки форм
    document.querySelectorAll('form input').forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.closest('form')?.submit();
            }
        });
    });

    // Валидация формы регистрации
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password');
            const confirm = document.getElementById('confirm_password');

            if (password && confirm && password.value !== confirm.value) {
                e.preventDefault();
                alert('❌ Пароли не совпадают!');
            }

            if (password && password.value.length < 12) {
                e.preventDefault();
                alert('❌ Пароль должен быть минимум 12 символов!');
            }
        });
    }
});