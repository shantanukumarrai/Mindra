import duckdb
import datetime

DB_PATH = 'meditation_streak.db'

def get_db_connection():
    """Return a fresh DuckDB connection."""
    return duckdb.connect(DB_PATH)

def init_database():
    """Create all required tables if they don't exist."""
    conn = get_db_connection()
    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    # Meditation logs (one per user per day)
    # we keep an explicit primary key since some versions of DuckDB don't
    # auto-increment. we will populate it manually in complete_meditation.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meditation_logs (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            meditation_date TEXT NOT NULL,
            UNIQUE(user_id, meditation_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Streak tracking (one row per user)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS streak_tracking (
            user_id INTEGER PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            highest_streak INTEGER DEFAULT 0,
            date TEXT DEFAULT NULL,  -- last_completed_date YYYY-MM-DD
            reminder_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.close()
    # Avoid emoji to prevent Windows console encoding errors
    print("DuckDB database initialized.")

def register_user(name, email, password_hash, reminder_time):
    """Create user and streak tracking row.

    DuckDB doesn't auto-increment integer primary keys, so we compute the
    next `id` ourselves. We also removed the `id` column from
    `meditation_logs` which was never used.
    """
    conn = get_db_connection()
    try:
        # figure out next user id
        row = conn.execute("SELECT MAX(id) FROM users").fetchone()
        next_id = (row[0] or 0) + 1

        conn.execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (next_id, name, email, password_hash)
        )

        user_id = next_id

        conn.execute("""
            INSERT INTO streak_tracking (user_id, current_streak, highest_streak, date, reminder_time)
            VALUES (?, 0, 0, NULL, ?)
        """, (user_id, reminder_time))
        conn.close()
        return user_id
    except Exception as e:
        conn.close()
        raise e

def get_user_by_email(email):
    """Return user tuple or None."""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,)
    ).fetchone()
    conn.close()
    return user

def get_streak_data(user_id):
    """Return current streak info."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT current_streak, highest_streak FROM streak_tracking WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return {'current': row[0], 'highest': row[1]}
    return {'current': 0, 'highest': 0}

def is_completed_today(user_id):
    """Check if meditation done today."""
    today = datetime.date.today().isoformat()
    conn = get_db_connection()
    res = conn.execute(
        "SELECT 1 FROM meditation_logs WHERE user_id = ? AND meditation_date = ?",
        (user_id, today)
    ).fetchone()
    conn.close()
    return res is not None

def complete_meditation(user_id):
    """
    Log today's meditation and update streak.
    Returns True if newly completed, False if already done today.
    """
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    conn = get_db_connection()
    try:
        # compute next log id since the column is not auto-populated
        row = conn.execute("SELECT MAX(id) FROM meditation_logs").fetchone()
        next_log_id = (row[0] or 0) + 1

        # Insert log (will fail if duplicate due to UNIQUE constraint)
        conn.execute(
            "INSERT INTO meditation_logs (id, user_id, meditation_date) VALUES (?, ?, ?)",
            (next_log_id, user_id, today)
        )
    except:
        conn.close()
        return False  # Already completed today

    # Get current streak
    row = conn.execute(
        "SELECT current_streak, highest_streak FROM streak_tracking WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    current_streak = row[0] if row else 0
    highest = row[1] if row else 0

    # Was yesterday completed?
    yest_done = conn.execute(
        "SELECT 1 FROM meditation_logs WHERE user_id = ? AND meditation_date = ?",
        (user_id, yesterday)
    ).fetchone() is not None

    new_streak = current_streak + 1 if yest_done else 1
    new_highest = max(highest, new_streak)

    # Update streak tracking
    conn.execute("""
        UPDATE streak_tracking 
        SET current_streak = ?, highest_streak = ?, date = ?
        WHERE user_id = ?
    """, (new_streak, new_highest, today, user_id))

    conn.close()
    return True