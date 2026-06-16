# database_manager.py
"""
Handles all database operations with connection pooling
"""

import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from pathlib import Path
import json
import numpy as np

class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.schema_path = Path(__file__).with_name('tables')
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,  # min and max connections
                host=config['host'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                port=config.get('port', 5432)
            )
            print("✓ Database connection pool created successfully")
            self.initialize_schema()
        except Exception as e:
            print(f"✗ Failed to create connection pool: {e}")
            raise

    def initialize_schema(self):
        """Create the prototype schema and seed data when needed."""
        if not self.schema_path.exists():
            print(f"⚠ Schema file not found: {self.schema_path}")
            return

        schema_sql = self.schema_path.read_text(encoding='utf-8')

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()

        print("✓ Prototype database schema verified")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = self.connection_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.connection_pool.putconn(conn)

    def get_all_classes(self):
        """Fetch all classes from database"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT class_id, class_name FROM Classes ORDER BY class_name")
                return {name: cid for cid, name in cur.fetchall()}

    def get_all_subjects(self):
        """Fetch all subjects from database"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT subject_id, subject_name FROM Subjects ORDER BY subject_name")
                return {name: sid for sid, name in cur.fetchall()}

    def register_student(self, prn, class_id, roll_no, name, email, face_encoding):
        """Register a new student with face encoding"""
        encoding_json = json.dumps(face_encoding.tolist())
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Insert student
                    cur.execute(
                        "INSERT INTO Students (prn_no, class_id, roll_no, name, email) VALUES (%s, %s, %s, %s, %s)",
                        (prn, class_id, int(roll_no), name, email)
                    )
                    # Insert face encoding
                    cur.execute(
                        "INSERT INTO FaceEncodings (prn_no, encoding_data) VALUES (%s, %s)",
                        (prn, encoding_json)
                    )
                    conn.commit()
                    return True, "Student registered successfully"
                except psycopg2.IntegrityError as e:
                    conn.rollback()
                    if "students_pkey" in str(e):
                        return False, f"PRN '{prn}' already exists"
                    elif "students_email_key" in str(e):
                        return False, f"Email '{email}' already exists"
                    elif "unique_roll_in_class" in str(e):
                        return False, f"Roll number '{roll_no}' already exists in this class"
                    else:
                        return False, str(e)

    def get_all_face_encodings(self):
        """Fetch all face encodings from database"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT prn_no, encoding_data FROM FaceEncodings")
                results = cur.fetchall()
                encodings = []
                prns = []
                for prn_no, encoding_data in results:
                    encodings.append(np.array(encoding_data))
                    prns.append(prn_no)
                return encodings, prns

    def log_attendance(self, prn_no, subject_id):
        """Log attendance for a student"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "INSERT INTO AttendanceLog (prn_no, subject_id) VALUES (%s, %s)",
                        (prn_no, subject_id)
                    )
                    conn.commit()
                    return True
                except Exception as e:
                    conn.rollback()
                    print(f"Error logging attendance: {e}")
                    return False

    def get_student_name(self, prn_no):
        """Get student name by PRN"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM Students WHERE prn_no = %s", (prn_no,))
                result = cur.fetchone()
                return result[0] if result else None

    def close(self):
        """Close all connections in the pool"""
        self.connection_pool.closeall()
