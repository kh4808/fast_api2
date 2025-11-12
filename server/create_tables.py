# create_tables.py
from server.database import Base, engine
from server.models import *


print("📦 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Done! Tables created successfully.")
