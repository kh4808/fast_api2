# create_tables.py
from database import Base, engine
from models import LevelTestLog

print("📦 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Done! Tables created successfully.")
