import psycopg2
from passlib.context import CryptContext
import os

RDS_HOST = os.environ['RDS_HOST']
RDS_PORT = os.environ['RDS_PORT']
RDS_DB_NAME = os.environ['RDS_DB_NAME']
RDS_USER = os.environ['RDS_USER']
RDS_PASSWORD = os.environ['RDS_PASSWORD']
DATABASE_URL = f"dbname='{RDS_DB_NAME}' user='{RDS_USER}' host='{RDS_HOST}' port={RDS_PORT} password='{RDS_PASSWORD}'"
# psql --host=assignment-3.cg4vo6ofeasg.us-east-1.rds.amazonaws.com --port=5432 --username=postgres --password --dbname=a3 

def get_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print("Unable to connect to the database")
        print(e)
        return None

def setup_database():
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    logs VARCHAR(255) DEFAULT NULL
                );
            """)
            conn.commit()
        except psycopg2.Error as e:
            print("Failed to create the 'users' table.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_password_hash(password):
    return pwd_context.hash(password)

def add_user(username, email, password, path):
    hashed_password = get_password_hash(password)  # Hash the password
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, email, password, logs) VALUES (%s, %s, %s, %s);", (username, email, hashed_password, path))
            conn.commit()
        except psycopg2.Error as e:
            print("Failed to add user.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def check_user(username, password):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT username, password FROM users WHERE username=%s;", (username,))
            user = cur.fetchone()
            if user:
                stored_password = user[1]
                return verify_password(password, stored_password)
        except psycopg2.Error as e:
            print("Error checking user.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    return False


def user_exists(username):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT username FROM users WHERE username=%s;", (username,))
            user = cur.fetchone()
            return bool(user)
        except psycopg2.Error as e:
            print("Error checking if user exists.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    return False

def email_exists(username):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT email FROM users WHERE email=%s;", (username,))
            user = cur.fetchone()
            return bool(user)
        except psycopg2.Error as e:
            print("Error checking if email exists.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    return False


def update_user_email(username, email):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("UPDATE users SET email = %s WHERE username = %s;", (email, username))
            conn.commit()
        except psycopg2.Error as e:
            print("Error updating user email.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()

def update_user_password(username, new_password):
    hashed_password = get_password_hash(new_password)
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("UPDATE users SET password = %s WHERE username = %s;", (hashed_password, username))
            conn.commit()
        except psycopg2.Error as e:
            print("Error updating user password.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()

def email_exists(email):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT email FROM users WHERE email = %s;", (email,))
            result = cur.fetchone()
            return bool(result)
        except psycopg2.Error as e:
            print("Error checking if email exists.")
            print(e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    return False


# Call setup_database to ensure tables are created when script runs
setup_database()
