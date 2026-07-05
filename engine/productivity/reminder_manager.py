"""
ReminderManager: SQLite-backed reminder store with background threading scheduler.
Fires TTS alerts when the reminder time is reached, even after restarts.
"""
import sqlite3
import threading
import os
import re
from datetime import datetime, timedelta

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "reminders.db"
)

class ReminderManager:
    _lock = threading.Lock()

    # ─── DB helpers ───────────────────────────────────────────────────────────

    @classmethod
    def _get_conn(cls) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task        TEXT    NOT NULL,
                remind_at   TEXT    NOT NULL,
                fired       INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        return conn

    # ─── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def add_reminder(cls, task: str, time_str: str) -> str:
        remind_at = cls._parse_time(time_str)
        if remind_at is None:
            return (
                f"I couldn't parse the time '{time_str}'. "
                "Try '5 PM', 'in 10 minutes', or '14:30'."
            )

        with cls._lock:
            conn = cls._get_conn()
            conn.execute(
                "INSERT INTO reminders (task, remind_at) VALUES (?, ?)",
                (task, remind_at.isoformat())
            )
            conn.commit()
            conn.close()

        # Schedule the alert
        delay = (remind_at - datetime.now()).total_seconds()
        if delay > 0:
            t = threading.Timer(delay, cls._fire_reminder, args=[task])
            t.daemon = True
            t.start()

        return f"Reminder set: '{task}' at {remind_at.strftime('%I:%M %p')}."

    @classmethod
    def list_reminders(cls) -> str:
        conn = cls._get_conn()
        rows = conn.execute(
            "SELECT id, task, remind_at FROM reminders WHERE fired = 0 ORDER BY remind_at"
        ).fetchall()
        conn.close()

        if not rows:
            return "You have no upcoming reminders, boss."

        lines = [
            f"[{r[0]}] '{r[1]}' at {datetime.fromisoformat(r[2]).strftime('%I:%M %p')}"
            for r in rows
        ]
        return "Your upcoming reminders: " + ". ".join(lines)

    @classmethod
    def delete_reminder(cls, reminder_id: int) -> str:
        with cls._lock:
            conn = cls._get_conn()
            cursor = conn.execute(
                "DELETE FROM reminders WHERE id = ?", (reminder_id,)
            )
            conn.commit()
            conn.close()
        if cursor.rowcount == 0:
            return f"No reminder found with ID {reminder_id}."
        return f"Reminder {reminder_id} deleted."

    @classmethod
    def restore_pending(cls):
        """Re-schedule reminders that survived a restart."""
        conn = cls._get_conn()
        rows = conn.execute(
            "SELECT id, task, remind_at FROM reminders WHERE fired = 0"
        ).fetchall()
        conn.close()

        now = datetime.now()
        for _, task, remind_at_str in rows:
            remind_at = datetime.fromisoformat(remind_at_str)
            delay = (remind_at - now).total_seconds()
            if delay > 0:
                t = threading.Timer(delay, cls._fire_reminder, args=[task])
                t.daemon = True
                t.start()

    # ─── Internals ────────────────────────────────────────────────────────────

    @classmethod
    def _fire_reminder(cls, task: str):
        # Mark as fired
        with cls._lock:
            conn = cls._get_conn()
            conn.execute(
                "UPDATE reminders SET fired = 1 WHERE task = ? AND fired = 0",
                (task,)
            )
            conn.commit()
            conn.close()

        from engine.voice.tts_engine import speak
        speak(f"Boss, reminder: {task}")
        print(f"[REMINDER] {task}")

    @classmethod
    def _parse_time(cls, time_str: str):
        """Parse natural language time expressions into a datetime."""
        ts = time_str.strip().lower()
        now = datetime.now()

        # "in X minutes/hours"
        m = re.match(r'in (\d+)\s+(minute|minutes|hour|hours)', ts)
        if m:
            amount = int(m.group(1))
            if 'hour' in m.group(2):
                return now + timedelta(hours=amount)
            return now + timedelta(minutes=amount)

        # "5 PM", "5:30 PM", "17:00", "5:30PM"
        for fmt in ['%I:%M %p', '%I %p', '%H:%M', '%I:%M%p', '%I%p']:
            try:
                t = datetime.strptime(ts.upper(), fmt)
                result = now.replace(
                    hour=t.hour, minute=t.minute, second=0, microsecond=0
                )
                if result <= now:
                    result += timedelta(days=1)
                return result
            except ValueError:
                continue

        return None
