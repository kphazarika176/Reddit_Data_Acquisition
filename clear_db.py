from src.database import DatabaseManager

db = DatabaseManager()

print("Clearing all database collections...")
db.clear_database()
print("\nDatabase cleared successfully!")
