import sqlite3

def init_db():
    conn = sqlite3.connect("payments.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        status TEXT DEFAULT 'pending'
    )""")
    conn.commit()
    conn.close()

def save_payment(payment_id, user_id):
    print(f"💾 Пытаемся сохранить payment_id={payment_id}, user_id={user_id}")
    try:
        conn = sqlite3.connect("payments.db")
        c = conn.cursor()
        c.execute("INSERT INTO payments (payment_id, user_id) VALUES (?, ?)", (payment_id, user_id))
        conn.commit()
        conn.close()
        print("✅ Успешно сохранено")
    except Exception as e:
        print(f"❌ Ошибка при сохранении в БД: {e}")


def mark_paid(payment_id):
    conn = sqlite3.connect("payments.db")
    c = conn.cursor()
    c.execute("UPDATE payments SET status='paid' WHERE payment_id=?", (payment_id,))
    conn.commit()
    conn.close()

def get_user_by_payment(payment_id):
    conn = sqlite3.connect("payments.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM payments WHERE payment_id=?", (payment_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None
