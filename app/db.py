import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./certigov.db')
# Neon provides postgresql:// URLs, SQLAlchemy must use the installed psycopg v3 driver.
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
kwargs = {'connect_args': {'check_same_thread': False, 'timeout': 30}} if DATABASE_URL.startswith('sqlite') else {'pool_pre_ping': True}
engine = create_engine(DATABASE_URL, future=True, **kwargs)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, future=True)
Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
