import os
import json
from datetime import datetime, date
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.secret_key = 'epilog_secret_key_change_in_production'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db_dir = os.path.join(app.root_path, '.database')
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'Users.db')

engine = create_engine(f'sqlite:///{db_path}')

with engine.connect() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    '''))
    
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            episode_type TEXT NOT NULL,
            trigger TEXT NOT NULL,
            location TEXT NOT NULL,
            details TEXT NOT NULL,
            time_1 TEXT,
            time_2 TEXT,
            log_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    '''))

    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            med_name TEXT NOT NULL,
            dosage TEXT,
            dosage_unit TEXT,
            reason TEXT,
            frequency TEXT,
            image_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    '''))
    conn.commit()

# --- AUTH ROUTES ---

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = "All fields are required."
        else:
            hashed_pw = generate_password_hash(password)
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text('INSERT INTO users (username, password_hash) VALUES (:u, :p)'),
                        {"u": username, "p": hashed_pw}
                    )
                    conn.commit()
                return redirect(url_for('login'))
            except Exception:
                error = "Username already exists. Please choose another."

    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        with engine.connect() as conn:
            result = conn.execute(
                text('SELECT id, password_hash FROM users WHERE username = :u'),
                {"u": username}
            ).fetchone()

        if result and check_password_hash(result[1], password):
            session['user_id'] = result[0]
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error = "Invalid username or password."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- SEIZURE LOG ROUTES ---

@app.route('/save_log', methods=['POST'])
def save_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    episode_type = request.form.get('episode_type')
    custom_episode_type = request.form.get('custom_episode_type', '').strip()
    trigger = request.form.get('trigger', '')
    custom_trigger = request.form.get('custom_trigger', '').strip()

    if episode_type == 'Other' and custom_episode_type:
        episode_type = custom_episode_type

    if trigger == 'Other' and custom_trigger:
        trigger = custom_trigger

    location = request.form.get('location', '')
    details = request.form.get('details', '')
    time_1 = request.form.get('time_1', '')
    time_2 = request.form.get('time_2', '')

    event_date = request.form.get('event_date')
    now = datetime.now()
    current_date = event_date if event_date else now.strftime("%Y-%m-%d")

    if episode_type and details:
        with engine.connect() as conn:
            conn.execute(
                text('''
                    INSERT INTO logs (user_id, episode_type, trigger, location, details, time_1, time_2, log_date) 
                    VALUES (:user_id, :type, :trigger, :location, :details, :time_1, :time_2, :date)
                '''),
                {
                    "user_id": user_id,
                    "type": episode_type,
                    "trigger": trigger,
                    "location": location,
                    "details": details, 
                    "time_1": time_1,
                    "time_2": time_2,
                    "date": current_date
                }
            )
            conn.commit()

    return redirect(url_for('summary'))

@app.route('/edit_log/<int:log_id>', methods=['POST'])
def edit_log(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    episode_type = request.form.get('episode_type')
    trigger = request.form.get('trigger', '')
    location = request.form.get('location', '')
    details = request.form.get('details', '')
    time_1 = request.form.get('time_1', '')
    time_2 = request.form.get('time_2', '')
    event_date = request.form.get('event_date', '')

    with engine.connect() as conn:
        conn.execute(
            text('''
                UPDATE logs 
                SET episode_type = :type, trigger = :trigger, location = :location, 
                    details = :details, time_1 = :time_1, time_2 = :time_2, log_date = :date
                WHERE id = :log_id AND user_id = :user_id
            '''),
            {
                "type": episode_type,
                "trigger": trigger,
                "location": location,
                "details": details,
                "time_1": time_1,
                "time_2": time_2,
                "date": event_date,
                "log_id": log_id,
                "user_id": user_id
            }
        )
        conn.commit()

    return redirect(url_for('summary'))

@app.route('/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM logs WHERE id = :log_id AND user_id = :user_id"),
            {"log_id": log_id, "user_id": user_id}
        )
        conn.commit()

    return redirect(url_for('summary'))

@app.route('/Log_Summary')
def summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    sort_order = request.args.get('sort', 'newest')
    selected_type = request.args.get('episode_type', '')
    selected_trigger = request.args.get('trigger', '')

    with engine.connect() as conn:
        type_results = conn.execute(
            text("SELECT DISTINCT episode_type FROM logs WHERE user_id = :user_id AND episode_type != '' ORDER BY episode_type ASC"),
            {"user_id": user_id}
        ).fetchall()
        episode_types = [row[0] for row in type_results]

        trigger_results = conn.execute(
            text("SELECT DISTINCT trigger FROM logs WHERE user_id = :user_id AND trigger != '' ORDER BY trigger ASC"),
            {"user_id": user_id}
        ).fetchall()
        triggers = [row[0] for row in trigger_results]

        query = "SELECT * FROM logs WHERE user_id = :user_id"
        params = {"user_id": user_id}

        if selected_type:
            query += " AND episode_type = :episode_type"
            params["episode_type"] = selected_type

        if selected_trigger:
            query += " AND trigger = :trigger"
            params["trigger"] = selected_trigger

        if sort_order == 'oldest':
            query += " ORDER BY created_at ASC"
        else:
            query += " ORDER BY created_at DESC"

        result = conn.execute(text(query), params)
        logs = result.fetchall()

    return render_template(
        'summary.html',
        logs=logs,
        episode_types=episode_types,
        triggers=triggers,
        selected_sort=sort_order,
        selected_type=selected_type,
        selected_trigger=selected_trigger
    )

# --- MEDICATION ROUTES ---

@app.route('/medical', methods=['GET', 'POST'])
def medical():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        med_name = request.form.get('med_name', '').strip()
        dosage = request.form.get('dosage', '').strip()
        dosage_unit = request.form.get('dosage_unit', '').strip()
        reason = request.form.get('reason', '').strip()
        frequency = request.form.get('frequency', '').strip()

        filename = None
        if 'med_image' in request.files:
            file = request.files['med_image']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{user_id}_{int(datetime.now().timestamp())}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                filename = unique_filename

        if med_name:
            with engine.connect() as conn:
                conn.execute(
                    text('''
                        INSERT INTO medications (user_id, med_name, dosage, dosage_unit, reason, frequency, image_filename)
                        VALUES (:u, :m, :d, :du, :r, :f, :img)
                    '''),
                    {
                        "u": user_id,
                        "m": med_name,
                        "d": dosage,
                        "du": dosage_unit,
                        "r": reason,
                        "f": frequency,
                        "img": filename
                    }
                )
                conn.commit()
            return redirect(url_for('medical'))

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM medications WHERE user_id = :u ORDER BY created_at DESC"),
            {"u": user_id}
        )
        medications = result.fetchall()

    return render_template('medical.html', medications=medications)

@app.route('/edit_medication/<int:med_id>', methods=['POST'])
def edit_medication(med_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    med_name = request.form.get('med_name', '').strip()
    dosage = request.form.get('dosage', '').strip()
    dosage_unit = request.form.get('dosage_unit', '').strip()
    reason = request.form.get('reason', '').strip()
    frequency = request.form.get('frequency', '').strip()

    filename = None
    if 'med_image' in request.files:
        file = request.files['med_image']
        if file and file.filename != '' and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{user_id}_{int(datetime.now().timestamp())}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            filename = unique_filename

    with engine.connect() as conn:
        if filename:
            conn.execute(
                text('''
                    UPDATE medications 
                    SET med_name = :m, dosage = :d, dosage_unit = :du, reason = :r, frequency = :f, image_filename = :img
                    WHERE id = :med_id AND user_id = :u
                '''),
                {"m": med_name, "d": dosage, "du": dosage_unit, "r": reason, "f": frequency, "img": filename, "med_id": med_id, "u": user_id}
            )
        else:
            conn.execute(
                text('''
                    UPDATE medications 
                    SET med_name = :m, dosage = :d, dosage_unit = :du, reason = :r, frequency = :f
                    WHERE id = :med_id AND user_id = :u
                '''),
                {"m": med_name, "d": dosage, "du": dosage_unit, "r": reason, "f": frequency, "med_id": med_id, "u": user_id}
            )
        conn.commit()

    return redirect(url_for('medical'))

@app.route('/delete_medication/<int:med_id>', methods=['POST'])
def delete_medication(med_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM medications WHERE id = :med_id AND user_id = :user_id"),
            {"med_id": med_id, "user_id": user_id}
        )
        conn.commit()

    return redirect(url_for('medical'))

# --- API & DATA ROUTES ---

@app.route('/api/last_seizure')
def api_last_seizure():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']

    with engine.connect() as conn:
        result = conn.execute(
            text('''
                SELECT log_date 
                FROM logs 
                WHERE user_id = :u AND log_date IS NOT NULL AND log_date != '' 
                ORDER BY log_date DESC 
                LIMIT 1
            '''),
            {"u": user_id}
        ).fetchone()

    if result and result[0]:
        try:
            last_date = datetime.strptime(result[0], "%Y-%m-%d").date()
            today = date.today()
            days_free = (today - last_date).days
            return jsonify({'days_free': max(0, days_free), 'last_date': result[0]})
        except ValueError:
            pass

    return jsonify({'days_free': 0, 'last_date': None})

@app.route('/data')
def data_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('data.html')

@app.route('/api/chart_data')
def api_chart_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']

    today = datetime.now()
    month_keys = []
    for i in range(11, -1, -1):
        m = today - relativedelta(months=i)
        month_keys.append(m.strftime("%Y-%m"))

    monthly_data = {month: 0 for month in month_keys}

    with engine.connect() as conn:
        month_query = text('''
            SELECT strftime('%Y-%m', log_date) as month_period, COUNT(id) as count 
            FROM logs 
            WHERE user_id = :u AND log_date IS NOT NULL AND log_date != ''
            GROUP BY month_period
        ''')
        month_result = conn.execute(month_query, {"u": user_id}).fetchall()

        trigger_query = text('''
            SELECT trigger, COUNT(id) as count
            FROM logs
            WHERE user_id = :u AND trigger IS NOT NULL AND trigger != ''
            GROUP BY trigger
            ORDER BY count DESC
        ''')
        trigger_result = conn.execute(trigger_query, {"u": user_id}).fetchall()

    for row in month_result:
        m_str, count = row[0], row[1]
        if m_str in monthly_data:
            monthly_data[m_str] = count

    return jsonify({
        'months': list(monthly_data.keys()),
        'counts': list(monthly_data.values()),
        'trigger_labels': [row[0] for row in trigger_result],
        'trigger_counts': [row[1] for row in trigger_result]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)