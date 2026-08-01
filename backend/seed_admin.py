import sys, os
sys.path.insert(0, r"c:\Users\83737\CodeBuddy\20260723213556\dc-ioc-platform\backend")
os.chdir(r"c:\Users\83737\CodeBuddy\20260723213556\dc-ioc-platform\backend")
from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models.user import User, Role

db = SessionLocal()
existing = db.query(User).filter(User.username == "admin").first()
if existing:
    print("admin already exists, skip")
else:
    admin = User(
        username="admin",
        email="admin@dcioc.local",
        display_name="Administrator",
        password_hash=hash_password("admin123"),
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print("created admin id=", admin.id)
db.close()
