from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import requests
from config import Config
import base64
from io import BytesIO
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from flask import make_response
import re

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

API_URL = Config.API_BASE_URL


def api_request(method, endpoint, data=None, token=None, use_form=False):
    """Универсальная функция для запросов к API"""
    headers = {}

    # ✅ ВАЖНО: правильно формируем заголовок Authorization
    if token:
        headers['Authorization'] = f'Bearer {token}'
        print(f"🔑 Токен отправлен: {token[:20]}...")
    else:
        print("⚠️ Токен отсутствует!")

    print(f"API Request: {method} {endpoint}")
    print(f"Headers: {headers}")
    print(f"Use form-data: {use_form}")

    try:
        if use_form:
            # Для /auth/login - отправляем как form-data
            response = requests.request(
                method,
                f'{API_URL}{endpoint}',
                data=data,
                headers=headers,
                timeout=10
            )
        else:
            # Для остальных - JSON
            response = requests.request(
                method,
                f'{API_URL}{endpoint}',
                json=data,
                headers=headers,  # ✅ Теперь headers включает Authorization!
                timeout=10
            )

        print(f"API Response: {response.status_code}")
        return response
    except Exception as e:
        print(f"API request error: {e}")
        return None


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@app.route('/')
def index():
    if 'token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        if not validate_email(email):
            flash('Некорректный формат email', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return redirect(url_for('register'))

        if len(password) < 12:
            flash('Пароль должен быть не менее 12 символов', 'error')
            return redirect(url_for('register'))

        if not re.search(r'[A-Z]', password):
            flash('Пароль должен содержать заглавную букву', 'error')
            return redirect(url_for('register'))

        if not re.search(r'[0-9]', password):
            flash('Пароль должен содержать цифру', 'error')
            return redirect(url_for('register'))

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Пароль должен содержать спецсимвол', 'error')
            return redirect(url_for('register'))

        data = {
            'email': email,
            'password': password,
            'role': role,
            'surname': request.form.get('surname', ''),
            'name': request.form.get('name', ''),
            'patronim': request.form.get('patronim', ''),
            'gender': request.form.get('gender', 'м'),
            'birth_date': request.form.get('birth_date', '2000-01-01'),
            'height': float(request.form.get('height')) if request.form.get('height') else None,
            'weight': float(request.form.get('weight')) if request.form.get('weight') else None
        }

        response = api_request('POST', '/auth/register', data)

        if response and response.status_code == 201:
            flash('Регистрация успешна! Теперь войдите в систему', 'success')
            return redirect(url_for('login'))
        elif response and response.status_code == 400:
            flash('Пользователь с таким email уже существует', 'error')
        else:
            flash('Ошибка при регистрации', 'error')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = {
            'username': request.form['email'],
            'password': request.form['password']
        }

        print("=" * 50)
        print("ЛОГИН: отправка form-data")
        print(f"Data: {data}")
        print("=" * 50)

        response = api_request('POST', '/auth/login', data=data, use_form=True)

        if response and response.status_code == 200:
            result = response.json()
            print(f"✅ УСПЕХ! Роль: {result['role']}")

            session['token'] = result['access_token']
            session['refresh_token'] = result['refresh_token']
            session['role'] = result['role']

            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('dashboard'))
        else:
            status = response.status_code if response else 'No response'
            print(f"❌ Ошибка: {status}")
            flash('Неверный логин или пароль', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    print(f"🚪 Выход из системы. Была сессия: {dict(session)}")
    session.clear()

    # Создаём ответ и удаляем куку сессии
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('session', '', expires=0)

    flash('Вы успешно вышли из системы', 'success')
    print("✅ Сессия очищена, кука удалена")
    return resp


@app.route('/dashboard')
def dashboard():
    if 'token' not in session:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('login'))

    if session['role'] == 'patient':
        return redirect(url_for('patient_dashboard'))
    elif session['role'] == 'doctor':
        return redirect(url_for('doctor_patients'))
    else:
        flash('Неизвестная роль пользователя', 'error')
        return redirect(url_for('login'))


@app.route('/patient/dashboard')
def patient_dashboard():
    if 'token' not in session or session['role'] != 'patient':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    print(f"🔑 Токен из сессии: {session['token'][:20]}...")

    response = api_request('GET', '/patient/profile', token=session['token'])

    if not response or response.status_code != 200:
        print(f"❌ Ошибка получения профиля: {response.status_code if response else 'No response'}")
        session.clear()
        flash('Сессия истекла, пожалуйста, войдите снова', 'error')
        return redirect(url_for('login'))

    profile = response.json()
    session['user_name'] = f"{profile['name']} {profile['surname']}"

    measurements_response = api_request('GET', '/patient/measurements', token=session['token'])
    measurements = measurements_response.json()[
        :10] if measurements_response and measurements_response.status_code == 200 else []

    last_measurement = measurements[0] if measurements else None
    current_date = datetime.now().strftime('%d.%m.%Y')

    return render_template(
        'patient_dashboard.html',
        profile=profile,
        measurements=measurements,
        last_measurement=last_measurement,
        current_date=current_date
    )


@app.route('/patient/measurements', methods=['GET', 'POST'])
def patient_measurements():
    if 'token' not in session or session['role'] != 'patient':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            'glucose': float(request.form.get('glucose')) if request.form.get('glucose') else None,
            'systolic_bp': int(request.form.get('systolic_bp')) if request.form.get('systolic_bp') else None,
            'diastolic_bp': int(request.form.get('diastolic_bp')) if request.form.get('diastolic_bp') else None,
            'pulse': int(request.form.get('pulse')) if request.form.get('pulse') else None,
            'weight': float(request.form.get('weight')) if request.form.get('weight') else None
        }

        response = api_request('POST', '/patient/measurements', data=data, token=session['token'])
        if response and response.status_code == 201:
            flash('Измерения добавлены успешно', 'success')
        else:
            flash('Ошибка при добавлении измерений', 'error')
        return redirect(url_for('patient_measurements'))

    response = api_request('GET', '/patient/measurements', token=session['token'])
    measurements = response.json() if response and response.status_code == 200 else []

    chart_url = None
    if measurements:
        plt.figure(figsize=(10, 6))

        glucose = [m['glucose'] for m in measurements[:30] if m.get('glucose')]
        glucose_dates = [datetime.fromisoformat(m['measured_at']).date() for m in measurements[:30] if m.get('glucose')]

        if glucose:
            plt.plot(glucose_dates, glucose, marker='o', label='Глюкоза (ммоль/л)')

        plt.xlabel('Дата')
        plt.ylabel('Значение')
        plt.title('Динамика глюкозы')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        chart_url = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    return render_template('patient_measurements.html', measurements=measurements[:50], chart_url=chart_url)


@app.route('/patient/prescriptions')
def patient_prescriptions():
    if 'token' not in session or session['role'] != 'patient':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    response = api_request('GET', '/patient/prescriptions', token=session['token'])
    prescriptions = response.json() if response and response.status_code == 200 else []
    return render_template('patient_prescriptions.html', prescriptions=prescriptions)


@app.route('/patient/complaints', methods=['GET', 'POST'])
def patient_complaints():
    if 'token' not in session or session['role'] != 'patient':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            'symptom_id': int(request.form['symptom_id']),
            'severity': request.form['severity'],
            'description': request.form.get('description')
        }
        response = api_request('POST', '/patient/complaints', data=data, token=session['token'])
        if response and response.status_code == 201:
            flash('Жалоба добавлена успешно', 'success')
        else:
            flash('Ошибка при добавлении жалобы', 'error')
        return redirect(url_for('patient_complaints'))

    response = api_request('GET', '/patient/complaints', token=session['token'])
    complaints = response.json() if response and response.status_code == 200 else []
    return render_template('patient_complaints.html', complaints=complaints)


@app.route('/patient/diary')
def patient_diary():
    return render_template('patient_diary.html')


@app.route('/patient/statistics')
def patient_statistics():
    return render_template('patient_statistics.html')


@app.route('/patient/visits')
def patient_visits():
    return render_template('patient_visits.html')


@app.route('/patient/settings')
def patient_settings():
    return render_template('patient_settings.html')


@app.route('/patient/help')
def patient_help():
    return render_template('patient_help.html')


@app.route('/patient/notifications')
def patient_notifications():
    return render_template('patient_notifications.html')


@app.route('/doctor/patients')
def doctor_patients():
    if 'token' not in session or session['role'] != 'doctor':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    response = api_request('GET', '/doctor/patients', token=session['token'])
    patients = response.json() if response and response.status_code == 200 else []
    return render_template('doctor_patients.html', patients=patients)


@app.route('/doctor/patient/<int:patient_id>/card')
def doctor_patient_card(patient_id):
    if 'token' not in session or session['role'] != 'doctor':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('login'))

    response = api_request('GET', f'/doctor/patient/{patient_id}/card', token=session['token'])

    if not response or response.status_code != 200:
        flash('Ошибка при загрузке карты пациента', 'error')
        return redirect(url_for('doctor_patients'))

    data = response.json()

    chart_url = None
    if data.get('measurements'):
        plt.figure(figsize=(12, 8))
        measurements = data['measurements'][:30]

        plt.subplot(2, 2, 1)
        glucose = [m['glucose'] for m in measurements if m.get('glucose')]
        glucose_dates = [datetime.fromisoformat(m['measured_at']).date() for m in measurements if m.get('glucose')]
        if glucose:
            plt.plot(glucose_dates, glucose, marker='o', color='blue')
            plt.title('Глюкоза')
            plt.grid(True)

        plt.subplot(2, 2, 2)
        systolic = [m['systolic_bp'] for m in measurements if m.get('systolic_bp')]
        diastolic = [m['diastolic_bp'] for m in measurements if m.get('diastolic_bp')]
        bp_dates = [datetime.fromisoformat(m['measured_at']).date() for m in measurements if m.get('systolic_bp')]
        if systolic and diastolic:
            plt.plot(bp_dates, systolic, marker='o', label='Систолическое')
            plt.plot(bp_dates, diastolic, marker='o', label='Диастолическое')
            plt.title('Артериальное давление')
            plt.legend()
            plt.grid(True)

        plt.subplot(2, 2, 3)
        pulse = [m['pulse'] for m in measurements if m.get('pulse')]
        pulse_dates = [datetime.fromisoformat(m['measured_at']).date() for m in measurements if m.get('pulse')]
        if pulse:
            plt.plot(pulse_dates, pulse, marker='o', color='green')
            plt.title('Пульс')
            plt.grid(True)

        plt.subplot(2, 2, 4)
        weight = [m['weight'] for m in measurements if m.get('weight')]
        weight_dates = [datetime.fromisoformat(m['measured_at']).date() for m in measurements if m.get('weight')]
        if weight:
            plt.plot(weight_dates, weight, marker='o', color='purple')
            plt.title('Вес')
            plt.grid(True)

        plt.tight_layout()
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        chart_url = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    return render_template('doctor_patient_card.html', data=data, chart_url=chart_url)


@app.route('/doctor/prescriptions', methods=['POST'])
def doctor_create_prescription():
    if 'token' not in session or session['role'] != 'doctor':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    response = api_request('POST', '/doctor/prescriptions', data=data, token=session['token'])

    if response and response.status_code == 201:
        return jsonify({'message': 'Назначение создано'}), 201
    else:
        return jsonify({'error': 'Ошибка при создании назначения'}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)