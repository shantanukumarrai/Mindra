import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from database import get_db_connection
from email_service import send_reminder_email

def check_reminders():
    """Run every minute: send reminders if time matches and not completed today."""
    conn = get_db_connection()
    today_str = datetime.date.today().isoformat()
    current_time_str = datetime.datetime.now().strftime("%H:%M")

    query = """
        SELECT u.id, u.email, u.name, s.reminder_time 
        FROM users u 
        JOIN streak_tracking s ON u.id = s.user_id
    """
    users = conn.execute(query).fetchall()

    for user_id, email, name, reminder_time in users:
        if reminder_time == current_time_str:
            # Check if already completed today
            completed = conn.execute(
                "SELECT 1 FROM meditation_logs WHERE user_id = ? AND meditation_date = ?",
                (user_id, today_str)
            ).fetchone()
            if not completed:
                send_reminder_email(email, name)

    conn.close()

def reset_streaks():
    """Run daily at 00:00: reset current streak to 0 if user missed yesterday."""
    conn = get_db_connection()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    users = conn.execute("SELECT user_id FROM streak_tracking").fetchall()

    for (user_id,) in users:
        completed_yesterday = conn.execute(
            "SELECT 1 FROM meditation_logs WHERE user_id = ? AND meditation_date = ?",
            (user_id, yesterday)
        ).fetchone()
        if not completed_yesterday:
            conn.execute(
                "UPDATE streak_tracking SET current_streak = 0 WHERE user_id = ?",
                (user_id,)
            )

    conn.close()
    print("Daily streak reset job completed.")

def start_scheduler():
    """Start background scheduler for reminders + daily reset."""
    scheduler = BackgroundScheduler()
    # Check reminders every minute
    scheduler.add_job(check_reminders, trigger='interval', minutes=1)
    # Reset streaks at midnight (server local time)
    scheduler.add_job(reset_streaks, trigger='cron', hour=0, minute=0)
    scheduler.start()
    # avoid emoji in logs
    print("APScheduler started - reminders every minute, streak reset at 00:00")
    return scheduler