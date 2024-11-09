function showTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.form').forEach(form => form.classList.remove('active'));
    document.querySelector(`.tab:nth-child(${tabName === 'login' ? '1' : '2'})`).classList.add('active');
    document.getElementById(`${tabName}Form`).classList.add('active');
}

function validateForm(formId) {
    const form = document.getElementById(formId);
    const inputs = form.querySelectorAll('input[required]');
    const errorDiv = document.getElementById(`${formId.replace('Form', 'Error')}`);
    const submitButton = form.querySelector('button[type="submit"]');

    let isValid = true;
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
        }
    });

    if (!isValid) {
        errorDiv.textContent = 'Пожалуйста, заполните все поля';
        submitButton.disabled = true;
    } else {
        errorDiv.textContent = '';
        submitButton.disabled = false;
    }

    return isValid;
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (validateForm('loginForm')) {
        const username = loginForm.querySelector('input[type="email"]').value;
        const password = loginForm.querySelector('input[type="password"]').value;

        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                window.location.href = '/messenger';
            } else {
                alert('Ошибка авторизации. Проверьте введенные данные.');
            }
        } catch (error) {
            console.error('Ошибка при отправке запроса:', error);
            alert('Произошла ошибка при попытке авторизации.');
        }
    }
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (validateForm('registerForm')) {
        const email = registerForm.querySelector('input[type="email"]').value;
        const firstName = registerForm.querySelector('input[placeholder="Имя"]').value;
        const lastName = registerForm.querySelector('input[placeholder="Фамилия"]').value;
        const password = registerForm.querySelector('input[type="password"]').value;

        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    "email": email,
                    "first_name": firstName,
                    "last_name": lastName,
                    "password": password
                }),
            });

            if (response.ok) {
                alert('Регистрация успешна!');
            } else {
                alert('Ошибка регистрации. Возможно, такой email уже существует.');
            }
        } catch (error) {
            console.error('Ошибка при отправке запроса:', error);
            alert('Произошла ошибка при попытке авторизации.');
        }
    }
});

// Добавляем слушатели событий для проверки полей в реальном времени
['loginForm', 'registerForm'].forEach(formId => {
    const form = document.getElementById(formId);
    form.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', () => validateForm(formId));
    });
});

// Инициализация валидации форм
validateForm('loginForm');
validateForm('registerForm');