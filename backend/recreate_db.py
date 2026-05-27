import sys
import os

# Добавляем путь к директории backend, чтобы можно было импортировать app
sys.path.append(os.path.dirname(__file__))

from app.database import engine, Base
from app.models import User, Vehicle, Tariff, Session, Payment

def recreate_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database recreated successfully.")

if __name__ == "__main__":
    recreate_db()
