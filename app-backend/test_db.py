from core.database import SessionLocal
from sqlalchemy import text


def test_db_connection():
    db = None
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        print("✅ Database connection OK:", result.scalar())
    except Exception as e:
        print("❌ Database connection failed:", e)
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    test_db_connection()
