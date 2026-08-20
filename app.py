from flask import Flask, request, render_template, redirect, url_for
from sqlalchemy import create_engine, text
from datetime import datetime

app = Flask(__name__)

# Engine connection to SQLite
engine = create_engine('sqlite:///.database/Users.db')

# Ensure table exists with date and time columns
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
    print('Loading homepage...')
    return render_template('index.html')

@app.route('/save_log', methods=['POST'])
def save_log():
    # Retrieve form data
    episode_type = request.form.get('episode_type') or request.form.get('log-title')
    details = request.form.get('details') or request.form.get('log-details')

    # Get current date and time
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")  # e.g., "2026-08-20"
    current_time = now.strftime("%H:%M:%S")  # e.g., "14:30:15"

    # Save entry along with date and time
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

    return redirect(url_for('home'))

@app.route('/Log_Summary')
def log_summary():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM logs ORDER BY created_at DESC"))
        logs = result.fetchall()
    return render_template('summary.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True, reloader_type='stat', port=5000)