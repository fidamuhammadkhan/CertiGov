"""Administrative bootstrap and diagnostics. Example: python manage.py create-admin"""
import os, sys, getpass
from app.main import initialize_database
from app.db import SessionLocal
from app.models import User
from app.security import password_hash


def main():
    if len(sys.argv)<2 or sys.argv[1] not in ('create-admin','check'):
        print('Usage: python manage.py create-admin | check');sys.exit(1)
    initialize_database()
    if sys.argv[1]=='check':
        print('Database initialized successfully.');return
    email=(os.getenv('INITIAL_ADMIN_EMAIL') or input('Admin email: ')).lower().strip()
    name=os.getenv('INITIAL_ADMIN_NAME') or input('Admin full name: ')
    pwd=os.getenv('INITIAL_ADMIN_PASSWORD') or getpass.getpass('Secure password (12+ characters): ')
    with SessionLocal() as db:
        if db.query(User).filter_by(email=email).first():
            sys.exit('Account already exists. No changes made.')
        admin=User(email=email,full_name=name,password_hash=password_hash(pwd),role='superadmin')
        db.add(admin);db.commit();print('Super administrator created:',email)

if __name__=='__main__':main()
