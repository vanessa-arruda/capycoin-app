from core.database import Base, engine
from models import Parent, Child, Activity

print("🔨 Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created.")
