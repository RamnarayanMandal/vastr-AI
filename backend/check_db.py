import traceback
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg2://vastrai:vastrai@localhost:5434/vastrai", pool_pre_ping=True)
with engine.connect() as conn:
    r = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
    for row in r:
        print(row[0])
print("---")
# try register logic
from app.config import settings
from app.database import SessionLocal
from app.models import User
db = SessionLocal()
try:
    existing = db.query(User).filter(User.email == "fixtest_check@example.com").first()
    if existing:
        db.delete(existing)
        db.commit()
    u = User(full_name="Fix", email="fixtest_check@example.com", mobile="9876543222")
    u.set_password("TestPass123!")
    db.add(u)
    db.commit()
    db.refresh(u)
    print("register OK:", u.id)
except Exception:
    print("register FAILED:")
    traceback.print_exc()
finally:
    db.close()
