import os
import sys
from getpass import getpass
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from tabulate import tabulate  # for displaying tables nicely
from models import User, engine
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

# Create a database session
SQLAsession = sessionmaker(bind=engine)
db_session = SQLAsession()

# Initialize inspector and metadata
inspector = inspect(engine)
metadata = MetaData()

# ------ Helper Functions ------

def create_user():
    print("\n---- Create New User ----")
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    email = input("Email: ").strip()
    password = getpass("Password (hidden): ")
    confirm_password = getpass("Confirm Password (hidden): ")
    user_type = input("User Type (doctor/patient/nurse): ").strip().lower()
    secret_code = getpass("Your Secret Code: ")

    if password != confirm_password:
        print("❌ Passwords do not match.")
        return
    
    hashed_password = generate_password_hash(password)

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hashed_password,
        user_type=user_type,
        secret_code=secret_code
    )

    try:
        db_session.add(new_user)
        db_session.commit()
        print(f"✅ User '{first_name} {last_name}' created successfully!\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        db_session.rollback()

def list_users():
    print("\n---- List Of Users ----")
    users = db_session.query(User).all()
    if users:
        table = [[user.id, user.first_name, user.last_name, user.email, user.user_type] for user in users]
        print(tabulate(table, headers=["ID", "First Name", "Last Name", "Email", "User Type"], tablefmt="pretty"))
    else:
        print("No users found.")

def delete_user():
    list_users()
    user_id = input("\nEnter the ID of the user to delete: ").strip()

    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if user:
            db_session.delete(user)
            db_session.commit()
            print(f"✅ User '{user.first_name} {user.last_name}' deleted successfully!\n")
        else:
            print('❌ User not found.')
    except Exception as e:
        print(f"❌ Error: {e}")
        db_session.rollback()

def update_user():
    list_users()
    user_id = input("\nEnter the ID of the user to update: ").strip()

    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if user:
            print(f"Updating user '{user.first_name} {user.last_name}'")
            user.first_name = input("New First Name: ").strip() or user.first_name
            user.last_name = input("New Last Name: ").strip() or user.last_name
            user.email = input("New Email: ").strip() or user.email
            user.user_type = input("New User Type (doctor/patient/nurse): ").strip().lower() or user.user_type
            db_session.commit()
            print(f"✅ User '{user.first_name} {user.last_name}' updated successfully!\n")
        else:
            print("❌ User not found.")
    except Exception as e:
        print(f"❌ Error: {e}")
        db_session.rollback()

def update_password():
    list_users()
    user_id = input("\nEnter the ID of the user to update the password: ").strip()
    new_password = getpass("Enter the new password: ").strip()
    confirm_password = getpass("Confirm the new password: ").strip()

    if new_password != confirm_password:
        print("❌ Passwords do not match.")
        return
    
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if user:
            hashed_password = generate_password_hash(new_password)
            user.password = hashed_password
            db_session.commit()
            print(f"✅ Password updated successfully for '{user.first_name} {user.last_name}'!\n")
        else:
            print("❌ User not found.")
    except Exception as e:
        print(f"❌ Error: {e}")
        db_session.rollback()

# |----- Controlling the whole DB -----|

def list_tables():
    """List all tables in the database nicely."""
    tables = inspector.get_table_names()
    if tables:
        print("\n📋 Tables in the database:")
        table_data = [[idx+1, name] for idx, name in enumerate(tables)]
        print(tabulate(table_data, headers=["#", "Table Name"], tablefmt="pretty"))
    else:
        print("❌ No tables found.")
    return tables

def select_table():
    """Select a table from the database."""
    tables = list_tables()
    if not tables:
        return None

    choice = input("Enter table name: ").strip()
    if choice in tables:
        return choice
    else:
        print("❌ Invalid table name.")
        return None

def view_records(table_name):
    with engine.connect() as connection:
        try:
            query = text(f"SELECT * FROM {table_name}")
            result = connection.execute(query)
            rows = result.fetchall()

            if not rows:
                print("📭 No records found.")
                return

            # Get column names
            columns = result.keys()
            data = [list(row) for row in rows]
            print("\n📋 Records:")
            print(tabulate(data, headers=columns, tablefmt="pretty"))
        except Exception as e:
            print(f"❌ Error viewing records: {e}")

def insert_into_table(table_name):
    """Insert a record into a specific table."""
    columns = inspector.get_columns(table_name)
    values = {}

    for column in columns:
        if column['name'] == 'id':
            continue  # Skip auto-increment ID
        value = input(f"Enter value for {column['name']}: ")
        values[column['name']] = value

    keys = ", ".join(values.keys())
    placeholders = ", ".join([f":{key}" for key in values.keys()])
    query = text(f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders})")

    try:
        with engine.connect() as connection:
            connection.execute(query, values)
            print(f"✅ Record inserted into {table_name}.")
    except SQLAlchemyError as e:
        print(f"❌ Error inserting record: {str(e)}")

def delete_from_table(table_name):
    record_id = input("Enter the ID of the record to delete: ")
    with engine.begin() as connection:
        try:
            query = text(f"DELETE FROM {table_name} WHERE id = :id")
            connection.execute(query, {'id': record_id})
            print(f"✅ Record with ID {record_id} deleted successfully!")
        except Exception as e:
            print(f"❌ Error deleting record: {e}")


def delete_table(table_name):
    confirmation = input(f"⚠️ Are you sure you want to DELETE the entire table '{table_name}'? (yes/no): ")
    if confirmation.lower() == 'yes':
        with engine.begin() as connection:
            try:
                query = text(f"DROP TABLE {table_name}")
                connection.execute(query)
                print(f"✅ Table '{table_name}' deleted successfully!")
            except Exception as e:
                print(f"❌ Error deleting table: {e}")
    else:
        print("❌ Cancelled deleting the table.")

def add_column_to_table(table_name):
    column_name = input("Enter new column name: ")
    column_type = input("Enter column type (e.g., VARCHAR(255), INT): ")

    try:
        with SQLAsession() as db_session:
            db_session.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            db_session.commit()
            print(f"✅ Column '{column_name}' added to '{table_name}' successfully.")
    except SQLAlchemyError as e:
        print(f"❌ Error: {e}")

def control_table_menu(table_name):
    while True:
        print(f"\n🟡 Control Table: {table_name}")
        print("1. View Records")
        print("2. Insert Record")
        print("3. Delete Record")
        print("4. Delete Table")
        print("5. Add Column")
        print("6. Back")
        choice = input("Enter your choice: ")

        if choice == '1':
            view_records(table_name)
        elif choice == '2':
            insert_into_table(table_name)
        elif choice == '3':
            delete_from_table(table_name)
        elif choice == '4':
            delete_table(table_name)
        elif choice == '5':
            add_column_to_table(table_name)
        elif choice == '6':
            break
        else:
            print("❌ Invalid choice. Please try again.")

# ======== MENUS ========

def user_management_menu():
    """Menu for managing users."""
    while True:
        print("\n🔵 User Management Menu")
        print("1. Create User")
        print("2. List Users")
        print("3. Update User")
        print("4. Update User Password")
        print("5. Delete User")
        print("6. Back to Main Menu")

        choice = input("Enter your choice: ").strip()

        if choice == '1':
            create_user()
        elif choice == '2':
            list_users()
        elif choice == '3':
            update_user()
        elif choice == '4':
            update_password()
        elif choice == '5':
            delete_user()
        elif choice == '6':
            break
        else:
            print("❌ Invalid choice. Please try again.")

def db_control_menu():
    """Menu for database table operations."""
    while True:
        print("\n🟠 Database Control Menu")
        print("1. View Tables")
        print("2. Select and Control a Table")
        print("3. Back to Main Menu")

        choice = input("Enter your choice: ").strip()

        if choice == '1':
            list_tables()
        elif choice == '2':
            table_name = select_table()
            if table_name:
                control_table_menu(table_name)
        elif choice == '3':
            break
        else:
            print("❌ Invalid choice. Please try again.")

# ======== MAIN PROGRAM ========

if __name__ == '__main__':
    while True:
        print("\n=== 🖥️  TELEHEALTH ADMIN CONSOLE ===")
        print("1. User Management")
        print("2. Database Control")
        print("3. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == '1':
            user_management_menu()
        elif choice == '2':
            db_control_menu()
        elif choice == '3':
            print("👋 Exiting Admin Console. farewell!")
            break
        else:
            print("❌ Invalid choice. Please try again.")