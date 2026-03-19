"""
قاعدة بيانات SQLite لتطبيق تسجيل الحضور
"""

import sqlite3
import json
import hashlib
import os
from datetime import datetime

DATABASE = 'attendance.db'

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول الطلاب - ✅ إضافة حقل qr_image
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            group_name TEXT NOT NULL,
            student_code TEXT UNIQUE NOT NULL,
            qr_code TEXT NOT NULL,
            qr_image TEXT,  -- ✅ حقل جديد لتخزين صورة QR كـ base64
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول المواد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            grade TEXT DEFAULT 'الأولى',
            course_type TEXT DEFAULT 'أول',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الحضور
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            group_name TEXT,
            attendance_date DATE DEFAULT CURRENT_DATE,
            attendance_time TIME DEFAULT CURRENT_TIME,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الإعدادات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL DEFAULT '{}'
        )
    ''')
    
    # إضافة مستخدم admin افتراضي
    cursor.execute('''
        INSERT OR IGNORE INTO users (id, username, password) 
        VALUES (1, 'admin', ?)
    ''', (hashlib.sha256('admin'.encode()).hexdigest(),))
    
    conn.commit()

    # ✅ Migration: أضف حقل qr_image إذا ما موجود (للقواعد القديمة)
    try:
        cursor.execute('ALTER TABLE students ADD COLUMN qr_image TEXT')
        conn.commit()
        print('[DB] Migration: qr_image column added successfully')
    except Exception:
        pass  # الحقل موجود مسبقاً - طبيعي

    conn.close()

def add_student(full_name, department, teacher_name, group_name, student_code, qr_code, qr_image=None):
    """إضافة طالب جديد - ✅ مع دعم تخزين صورة QR"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO students (full_name, department, teacher_name, group_name, student_code, qr_code, qr_image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (full_name, department, teacher_name, group_name, student_code, qr_code, qr_image))
        
        conn.commit()
        student_id = cursor.lastrowid
        return student_id
    except Exception as e:
        print(f"Error adding student: {e}")
        return None
    finally:
        conn.close()

def get_student_by_id(student_id):
    """الحصول على طالب بواسطة ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    conn.close()
    
    if student:
        return dict(student)
    return None

def get_student_by_code(student_code):
    """الحصول على طالب بواسطة كود الطالب"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students WHERE student_code = ?', (student_code,))
    student = cursor.fetchone()
    
    conn.close()
    
    if student:
        return dict(student)
    return None

def get_all_students():
    """الحصول على جميع الطلاب"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM students ORDER BY created_at DESC')
        students = cursor.fetchall()
        
        conn.close()
        
        if students:
            return [dict(student) for student in students]
        return []  # ✅ ارجع list فارغة بدل None
    except Exception as e:
        print(f'[DB Error] get_all_students: {e}')
        return []  # ✅ ارجع list فارغة عند أي خطأ

def delete_student(student_id):
    """حذف طالب"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # حذف سجلات الحضور أولاً
        cursor.execute('DELETE FROM attendance WHERE student_id = ?', (student_id,))
        # ثم حذف الطالب
        cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
        
        conn.commit()
        conn.close()
        print(f'[DB] Student {student_id} deleted successfully')
        return True
    except Exception as e:
        print(f'[DB Error] delete_student: {e}')
        return False

# ... باقي الدوال تبقى كما هي (add_subject, get_all_subjects, etc.)

def add_subject(name, code, department, teacher_name, grade='الأولى', course_type='أول'):
    """إضافة مادة جديدة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO subjects (name, code, department, teacher_name, grade, course_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, code, department, teacher_name, grade, course_type))
        
        conn.commit()
        subject_id = cursor.lastrowid
        return subject_id
    except Exception as e:
        print(f"Error adding subject: {e}")
        return None
    finally:
        conn.close()

def get_all_subjects():
    """الحصول على جميع المواد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM subjects ORDER BY created_at DESC')
        subjects = cursor.fetchall()
        
        conn.close()
        
        if subjects:
            return [dict(subject) for subject in subjects]
        return []  # ✅ ارجع list فارغة بدل None
    except Exception as e:
        print(f'[DB Error] get_all_subjects: {e}')
        return []  # ✅ ارجع list فارغة عند أي خطأ

def get_subjects_by_department(department):
    """الحصول على المواد حسب القسم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM subjects WHERE department = ?', (department,))
        subjects = cursor.fetchall()
        
        conn.close()
        
        return [dict(subject) for subject in subjects] if subjects else []
    except Exception as e:
        print(f'[DB Error] get_subjects_by_department: {e}')
        return []

def delete_subject(subject_id):
    """حذف مادة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM attendance WHERE subject_id = ?', (subject_id,))
        cursor.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        
        conn.commit()
        conn.close()
        print(f'[DB] Subject {subject_id} deleted successfully')
        return True
    except Exception as e:
        print(f'[DB Error] delete_subject: {e}')
        return False

def record_attendance(student_id, subject_id, group_name=None):
    """تسجيل حضور طالب"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من عدم تسجيل الحضور مسبقاً لهذا اليوم
    today = datetime.now().date()
    cursor.execute('''
        SELECT * FROM attendance 
        WHERE student_id = ? AND subject_id = ? AND attendance_date = ?
    ''', (student_id, subject_id, today))
    
    if cursor.fetchone():
        conn.close()
        return False  # مسجل مسبقاً
    
    # تسجيل الحضور
    cursor.execute('''
        INSERT INTO attendance (student_id, subject_id, group_name, attendance_date, attendance_time)
        VALUES (?, ?, ?, CURRENT_DATE, CURRENT_TIME)
    ''', (student_id, subject_id, group_name))
    
    conn.commit()
    conn.close()
    return True

def get_attendance_by_subject(subject_id, date=None):
    """الحصول على سجل الحضور لمادة معينة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT a.*, s.full_name, s.student_code, s.department, s.teacher_name, s.group_name
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.subject_id = ? AND a.attendance_date = ?
                ORDER BY a.attendance_time DESC
            ''', (subject_id, date))
        else:
            cursor.execute('''
                SELECT a.*, s.full_name, s.student_code, s.department, s.teacher_name, s.group_name
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.subject_id = ?
                ORDER BY a.attendance_date DESC, a.attendance_time DESC
            ''', (subject_id,))
        
        attendance = cursor.fetchall()
        conn.close()
        
        return [dict(record) for record in attendance] if attendance else []
    except Exception as e:
        print(f'[DB Error] get_attendance_by_subject: {e}')
        return []

def get_attendance_by_student(student_id):
    """الحصول على سجل حضور طالب"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT a.*, sub.name as subject_name, sub.teacher_name as subject_teacher
            FROM attendance a
            JOIN subjects sub ON a.subject_id = sub.id
            WHERE a.student_id = ?
            ORDER BY a.attendance_date DESC, a.attendance_time DESC
        ''', (student_id,))
        
        attendance = cursor.fetchall()
        conn.close()
        
        return [dict(record) for record in attendance] if attendance else []
    except Exception as e:
        print(f'[DB Error] get_attendance_by_student: {e}')
        return []

def get_today_attendance_stats():
    """إحصائيات حضور اليوم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT student_id) as total_students,
                   COUNT(*) as total_records
            FROM attendance
            WHERE attendance_date = ?
        ''', (today,))
        
        stats = cursor.fetchone()
        conn.close()
        
        return dict(stats) if stats else {'total_students': 0, 'total_records': 0}
    except Exception as e:
        print(f'[DB Error] get_today_attendance_stats: {e}')
        return {'total_students': 0, 'total_records': 0}

def get_last_attendance_time(student_id):
    """الحصول على وقت آخر حضور للطالب"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT attendance_date, attendance_time 
        FROM attendance 
        WHERE student_id = ? 
        ORDER BY attendance_date DESC, attendance_time DESC 
        LIMIT 1
    ''', (student_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        date_str = result['attendance_date']
        time_str = result['attendance_time']
        
        # ✅ تفقد إذا كانت الوقت null
        if not time_str:
            time_str = '00:00:00'
        
        try:
            # SQLite قد يرجع الوقت بـ HH:MM:SS أو HH:MM
            if time_str and len(time_str) == 5:  # HH:MM
                time_str = time_str + ':00'
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as e:
            print(f'[DB Error] get_last_attendance_time: {e}')
            return None
    return None

def get_student_group_name(student_id):
    """الحصول على اسم مجموعة الطالب"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT group_name FROM students WHERE id = ?', (student_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result['group_name'] if result else 'غير معروف'
    except Exception as e:
        print(f'[DB Error] get_student_group_name: {e}')
        return 'غير معروف'

# دوال المستخدمين
def verify_user(username, password):
    """التحقق من بيانات المستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
            SELECT * FROM users 
            WHERE username = ? AND password = ?
        ''', (username, hashed_password))
        
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    except Exception as e:
        print(f'[DB Error] verify_user: {e}')
        return None

def change_user_password(username, current_password, new_password):
    """تغيير كلمة مرور المستخدم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من كلمة المرور الحالية
    hashed_current = hashlib.sha256(current_password.encode()).hexdigest()
    cursor.execute('''
        SELECT * FROM users 
        WHERE username = ? AND password = ?
    ''', (username, hashed_current))
    
    if not cursor.fetchone():
        conn.close()
        return False
    
    # تحديث كلمة المرور
    hashed_new = hashlib.sha256(new_password.encode()).hexdigest()
    cursor.execute('''
        UPDATE users 
        SET password = ? 
        WHERE username = ?
    ''', (hashed_new, username))
    
    conn.commit()
    conn.close()
    return True

def get_all_users():
    """الحصول على جميع المستخدمين (بدون كلمات المرور)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, created_at FROM users')
    users = cursor.fetchall()
    
    conn.close()
    
    return [dict(user) for user in users]

def add_new_user(username, password):
    """إضافة مستخدم جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (username, password)
            VALUES (?, ?)
        ''', (username, hashed_password))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # اسم المستخدم موجود مسبقاً
    finally:
        conn.close()

def delete_user_by_username(username):
    """حذف مستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        
        conn.commit()
        conn.close()
        print(f'[DB] User {username} deleted successfully')
        return True
    except Exception as e:
        print(f'[DB Error] delete_user_by_username: {e}')
        return False

# دوال الإعدادات
def get_settings():
    """الحصول على إعدادات النظام"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT data FROM settings WHERE id = 1')
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return json.loads(result['data'])
    return {}

def save_settings(settings_dict):
    """حفظ إعدادات النظام"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    settings_json = json.dumps(settings_dict)
    
    cursor.execute('''
        INSERT OR REPLACE INTO settings (id, data)
        VALUES (1, ?)
    ''', (settings_json,))
    
    conn.commit()
    conn.close()