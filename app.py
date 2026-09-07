import os
from flask import Flask, request, render_template, redirect, url_for
from sqlalchemy import create_engine, text
from datetime import datetime

app = Flask(__name__)

# Ensure the database directory exists
db_dir = os.path.join(app.root_path, '.database')
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'Users.db')

# Engine connection to SQLite
engine = create_engine(f'sqlite:///{db_path}')

# Ensure table exists
with engine.connect() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_type TEXT NOT NULL,
            details TEXT NOT NULL,
            log_date TEXT NOT NULL,
            log_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''))
    conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/save_log', methods=['POST'])
def save_log():
    episode_type = request.form.get('episode_type') or request.form.get('log-title')
    details = request.form.get('details') or request.form.get('log-details')

    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    if episode_type and details:
        with engine.connect() as conn:
            conn.execute(
                text('''
                    INSERT INTO logs (episode_type, details, log_date, log_time) 
                    VALUES (:type, :details, :date, :time)
                '''),
                {
                    "type": episode_type, 
                    "details": details, 
                    "date": current_date, 
                    "time": current_time
                }
            )
            conn.commit()

    # Redirect directly to the summary page to see the new entry
    return redirect(url_for('log_summary'))

@app.route('/Log_Summary')
def log_summary():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM logs ORDER BY created_at DESC"))
        logs = result.fetchall()
    return render_template('summary.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True, port=5000)