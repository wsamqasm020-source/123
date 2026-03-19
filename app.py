"""
تطبيق تسجيل الحضور بالـ QR
Flask Web Application
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, send_from_directory
from functools import wraps
import qrcode
import io
import base64
import os
import hashlib
from datetime import datetime, timedelta
from database import (
    init_database, add_student, get_student_by_code, get_student_by_id,
    get_all_students, add_subject, get_all_subjects, get_subjects_by_department,
    record_attendance, get_attendance_by_subject, get_attendance_by_student,
    get_today_attendance_stats, delete_student, delete_subject,
    get_student_group_name, get_last_attendance_time, verify_user, change_user_password,
    get_settings, save_settings, get_all_users, add_new_user, delete_user_by_username
)


app = Flask(__name__)
app.secret_key = 'qr_attendance_secret_key_2026'

# ✅ إبقاء الـ session حية لمدة 7 أيام بدل انتهائها عند إغلاق المتصفح
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ✅ تهيئة قاعدة البيانات عند بدء التشغيل
with app.app_context():
    init_database()

# فترة المنع بين تسجيلات الحضور (بالدقائق)
COOLDOWN_MINUTES = 15


def login_required(f):
    """ديكوريتور للتحقق من تسجيل الدخول"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # مسح أي رسائل قديمة لتجنب التكرار
            session.pop('_flashes', None)
            flash('يرجى تسجيل الدخول أولاً', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """ديكوريتور للتحقق من أن المستخدم هو الـ admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('username') != 'admin':
            flash('هذه الصفحة متاحة فقط للمدير', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def generate_qr_code(data):
    """توليد QR code من البيانات - دالة موحدة"""
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    return qr.make_image(fill_color="black", back_color="white")


def qr_to_base64(img):
    """تحويل صورة QR إلى base64"""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def generate_student_code(department, teacher_name, group_name):
    """توليد رقم طالب فريد"""
    dept_prefix = department[:2].upper() if department else 'XX'
    teacher_prefix = teacher_name[:2].upper() if teacher_name else 'XX'
    group_prefix = group_name[:2].upper() if group_name else 'XX'
    
    prefix = f"{dept_prefix}{teacher_prefix}{group_prefix}"
    
    students = get_all_students()
    max_num = 0
    for student in students:
        if student['student_code'].startswith(prefix):
            try:
                num = int(student['student_code'][-3:])
                max_num = max(max_num, num)
            except:
                pass
    
    new_num = max_num + 1
    return f"{prefix}{new_num:03d}"


def check_attendance_cooldown(student_id):
    """التحقق من فترة المنع بين تسجيلات الحضور"""
    last_attendance = get_last_attendance_time(student_id)
    
    if not last_attendance:
        return True, 0
    
    current_time = datetime.now()
    elapsed_seconds = (current_time - last_attendance).total_seconds()
    cooldown_seconds = COOLDOWN_MINUTES * 60
    
    if elapsed_seconds < cooldown_seconds:
        remaining_seconds = int(cooldown_seconds - elapsed_seconds)
        return False, remaining_seconds
    
    return True, 0


def format_remaining_time(seconds):
    """تنسيق الوقت المتبقي بالدقائق والثواني"""
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes} دقيقة و {secs} ثانية"
    return f"{secs} ثانية"


# ============================================
# 🔥 ROUTE مهم جداً للـ Service Worker
# ============================================

@app.route('/sw.js')
def service_worker():
    """تقديم Service Worker"""
    response = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@app.route('/offline.html')
def offline_page():
    """صفحة Offline"""
    return send_from_directory('static', 'offline.html')


@app.route('/api/ping')
def api_ping():
    """✅ Keep-alive endpoint — بدون login_required حتى يشتغل دائماً"""
    if 'user_id' in session:
        # جدد الـ session تلقائياً
        session.permanent = True
        session.modified = True
        return jsonify({'status': 'ok', 'authenticated': True})
    return jsonify({'status': 'ok', 'authenticated': False}), 200


# ============================================
# Routes تسجيل الدخول (بدون حماية)
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    settings = get_settings()
    
    # إذا المستخدم مسجل دخول خليه يروح للرئيسية مباشرة
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = verify_user(username, password)
        
        if user:
            session.permanent = True  # ✅ ابقِ الـ session حية
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html', settings=settings)

@app.route('/logout')
def logout():
    """تسجيل الخروج"""
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))


@app.route('/change-password', methods=['POST'])
def change_password():
    """تغيير كلمة المرور"""
    username = request.form.get('username')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password != confirm_password:
        flash('كلمة المرور الجديدة غير متطابقة', 'error')
        return redirect(url_for('login'))
    
    if len(new_password) < 6:
        flash('يجب أن تكون كلمة المرور 6 أحرف على الأقل', 'error')
        return redirect(url_for('login'))
    
    if change_user_password(username, current_password, new_password):
        flash('تم تغيير كلمة المرور بنجاح!', 'success')
    else:
        flash('اسم المستخدم أو كلمة المرور الحالية غير صحيحة', 'error')
    
    return redirect(url_for('login'))


# ============================================
# Routes المحمية (تتطلب تسجيل دخول)
# ============================================

@app.route('/')
@login_required
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')


@app.route('/generate')
@login_required
def generate_page():
    """صفحة توليد QR"""
    return render_template('generate.html')


@app.route('/api/generate-qr', methods=['POST'])
@login_required
def generate_qr():
    """توليد QR Code وحفظه في قاعدة البيانات"""
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({'success': False, 'message': 'بيانات غير صالحة'}), 400

        full_name = data.get('full_name', '').strip()
        department = data.get('department', '').strip()
        teacher_name = data.get('teacher_name', '').strip()
        group_name = data.get('group_name', '').strip()

        if not all([full_name, department, teacher_name, group_name]):
            return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'}), 400
        
        import uuid
        student_code = str(uuid.uuid4())[:8].upper()

        # ✅ محتوى QR Code موحد
        qr_content = f"CODE:{student_code}|NAME:{full_name}|DEPT:{department}|TEACHER:{teacher_name}|GROUP:{group_name}"
        
        # ✅ استخدام نفس دالة التوليد الموحدة
        qr_img = generate_qr_code(qr_content)
        
        # ✅ تحويل الصورة إلى base64
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # ✅ حفظ الطالب مع الصورة في قاعدة البيانات
        student_id = add_student(full_name, department, teacher_name, group_name, student_code, qr_content, qr_base64)
        
        if not student_id:
            return jsonify({'success': False, 'message': 'فشل إضافة الطالب'}), 400
        
        # ✅ جلب الطالب المضاف للتأكد من إضافته
        student = get_student_by_id(student_id)
        
        if not student:
            return jsonify({'success': False, 'message': 'خطأ: لم يتم حفظ الطالب'}), 400
        
        print(f'[API] ✅ Student added: {full_name} ({student_code})')
        
        return jsonify({
            'success': True,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'student_code': student_code,
            'student': student,  # ✅ إرسال بيانات الطالب المضاف
            'message': 'تم التوليد والحفظ بنجاح'
        })
        
    except Exception as e:
        import traceback
        print(f"[API Error] generate_qr: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/scanner')
@login_required
def scanner_page():
    """صفحة ماسح QR"""
    subjects = get_all_subjects()
    return render_template('scanner.html', subjects=subjects)


@app.route('/api/scan-qr', methods=['POST'])
@login_required
def api_scan_qr():
    """API لمسح QR code وتسجيل الحضور"""
    try:
        data = request.get_json(force=True, silent=True)
    except Exception as e:
        print(f'[API] JSON Parse Error: {e}')
        return jsonify({'success': False, 'message': 'بيانات غير صالحة'}), 400

    if not data:
        return jsonify({'success': False, 'message': 'بيانات غير صالحة'}), 400

    qr_data = data.get('qr_data')
    subject_id = data.get('subject_id')

    if not qr_data or not subject_id:
        return jsonify({'success': False, 'message': 'بيانات غير كاملة'}), 400

    # ✅ تحويل subject_id لـ integer دائماً
    try:
        subject_id = int(subject_id)
    except (ValueError, TypeError) as e:
        print(f'[API] Subject ID conversion error: {e}')
        return jsonify({'success': False, 'message': 'subject_id غير صالح'}), 400

    try:
        # ✅ تنظيف QR data
        qr_data = str(qr_data).strip()
        print(f'[API] Processing QR: {qr_data}, Subject: {subject_id}')
        
        # ✅ محاولة استخراج student_code من format مختلفة
        student_code = None
        
        # Format 1: CODE:12345|NAME... (with pipes)
        if 'CODE:' in qr_data:
            code_start = qr_data.find('CODE:') + 5
            code_end = qr_data.find('|', code_start)
            if code_end == -1:
                code_end = len(qr_data)
            student_code = qr_data[code_start:code_end].strip()
        else:
            # Format 2: Just the code
            student_code = qr_data.strip()

        print(f'[API] Extracted student code: {student_code}')

        # ✅ البحث عن الطالب
        student = None
        try:
            students = get_all_students()
            if not students:
                print('[API] No students found in database')
                students = []
        except Exception as e:
            print(f'[API] Error getting students: {e}')
            students = []
        
        for s in students:
            if (s.get('qr_code') == qr_data or 
                s.get('student_code') == student_code or
                student_code in str(s.get('qr_code', ''))):
                student = s
                print(f'[API] Found student: {s.get("full_name")}')
                break

        if not student:
            print(f'[API] Student not found: {student_code}')
            return jsonify({
                'success': False, 
                'message': f'الطالب غير موجود (Code: {student_code})'
            }), 404

        # ✅ التحقق من فترة المنع
        student_id = student.get('id')
        if not student_id:
            print('[API] Student ID is None')
            return jsonify({
                'success': False,
                'message': 'خطأ: بيانات الطالب غير صحيحة'
            }), 400

        can_record, remaining_seconds = check_attendance_cooldown(student_id)

        if not can_record:
            remaining_time = format_remaining_time(remaining_seconds)
            print(f'[API] Cooldown active, remaining: {remaining_time}')
            return jsonify({
                'success': False,
                'message': f'⏳ فترة المنع! يرجى الانتظار {remaining_time} قبل إعادة التسجيل',
                'cooldown_active': True,
                'remaining_seconds': remaining_seconds,
                'remaining_time_formatted': remaining_time
            }), 429

        # ✅ تسجيل الحضور
        group_name = student.get('group_name', 'غير معروف')
        success = record_attendance(student_id, subject_id, group_name)

        if success:
            try:
                subjects = get_all_subjects()
                if not subjects:
                    subjects = []
            except Exception as e:
                print(f'[API] Error getting subjects: {e}')
                subjects = []

            subject = None
            if subjects and len(subjects) > 0:
                for s in subjects:
                    if s.get('id') == subject_id:
                        subject = s
                        break
            
            print(f'[API] ✅ Attendance recorded successfully')
            return jsonify({
                'success': True,
                'message': f"✅ تم تسجيل حضور {student.get('full_name', 'الطالب')} بنجاح",
                'student': student,
                'subject': subject,
                'group_name': group_name
            })
        else:
            print(f'[API] Attendance already recorded for this day')
            return jsonify({
                'success': False,
                'message': 'الطالب مسجل حضور مسبقاً لهذا اليوم في هذه المادة',
                'already_registered': True,
                'student': student
            }), 400

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f'[ERROR] {error_msg}')
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'خطأ في السيرفر: {error_msg}'
        }), 500


@app.route('/students')
@login_required
def students_page():
    """صفحة قائمة الطلاب"""
    students = get_all_students()
    return render_template('students.html', students=students)


@app.route('/student/<int:student_id>')
@login_required
def student_detail(student_id):
    """صفحة تفاصيل الطالب - ✅ استخدام الصورة المخزنة"""
    student = get_student_by_id(student_id)
    if not student:
        flash('الطالب غير موجود', 'error')
        return redirect(url_for('students_page'))
    
    attendance = get_attendance_by_student(student_id)
    
    # ✅ استخدام الصورة المخزنة في قاعدة البيانات
    qr_base64 = student.get('qr_image')
    
    # ✅ للطلاب القدامى الذين ليس لديهم صورة مخزنة، نولدها مؤقتاً
    if not qr_base64:
        qr_img = generate_qr_code(student['qr_code'])
        qr_base64 = qr_to_base64(qr_img).replace('data:image/png;base64,', '')
    
    return render_template('student_detail.html', 
                         student=student, 
                         attendance=attendance,
                         qr_code=f"data:image/png;base64,{qr_base64}")

@app.route('/subjects')
@login_required
def subjects_page():
    """صفحة المواد"""
    subjects = get_all_subjects()
    return render_template('subjects.html', subjects=subjects)

@app.route('/api/add-subject', methods=['POST'])
@login_required
def api_add_subject():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'لم يتم استلام أي بيانات'}), 400
        
        name = data.get('name')
        department = data.get('department')
        teacher_name = data.get('teacher_name')
        grade = data.get('grade', 'الأولى')
        course_type = data.get('course_type', 'أول')
        
        if not all([name, department, teacher_name, grade, course_type]):
            return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'}), 400
        
        import uuid
        code = str(uuid.uuid4())[:6].upper()
        
        subject_id = add_subject(name, code, department, teacher_name, grade, course_type)
        
        if subject_id:
            return jsonify({'success': True, 'subject_id': subject_id})
        else:
            return jsonify({'success': False, 'message': 'حدث خطأ في إضافة المادة'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطأ في الخادم: {str(e)}'}), 500


@app.route('/attendance')
@login_required
def attendance_page():
    """صفحة سجل الحضور"""
    subjects = get_all_subjects()
    today = datetime.now().strftime('%Y-%m-%d')
    today_stats = get_today_attendance_stats()
    
    return render_template('attendance.html', 
                         subjects=subjects,
                         today=today,
                         today_stats=today_stats)


@app.route('/api/attendance/<int:subject_id>')
@login_required
def api_get_attendance(subject_id):
    """API للحصول على سجل الحضور"""
    date = request.args.get('date')
    attendance = get_attendance_by_subject(subject_id, date)
    
    subjects = get_all_subjects()
    subject = next((s for s in subjects if s['id'] == subject_id), None)
    
    return jsonify({
        'success': True, 
        'attendance': attendance,
        'subject': subject
    })


@app.route('/api/delete-student/<int:student_id>', methods=['DELETE'])
@login_required
def api_delete_student(student_id):
    """API لحذف طالب"""
    try:
        success = delete_student(student_id)
        if success:
            return jsonify({'success': True, 'message': 'تم حذف الطالب بنجاح'})
        else:
            return jsonify({'success': False, 'message': 'فشل حذف الطالب'}), 400
    except Exception as e:
        print(f'[API Error] delete_student: {e}')
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}'}), 500


@app.route('/api/delete-subject/<int:subject_id>', methods=['DELETE'])
@login_required
def api_delete_subject(subject_id):
    """API لحذف مادة"""
    try:
        success = delete_subject(subject_id)
        if success:
            return jsonify({'success': True, 'message': 'تم حذف المادة بنجاح'})
        else:
            return jsonify({'success': False, 'message': 'فشل حذف المادة'}), 400
    except Exception as e:
        print(f'[API Error] delete_subject: {e}')
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}'}), 500


@app.route('/api/get-subjects')
@login_required
def api_get_subjects():
    """API للحصول على المواد"""
    try:
        department = request.args.get('department')
        
        if department:
            subjects = get_subjects_by_department(department)
        else:
            subjects = get_all_subjects()
        
        if subjects is None:
            subjects = []
        
        return jsonify({'success': True, 'subjects': subjects})
    except Exception as e:
        print(f'[API Error] api_get_subjects: {e}')
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}', 'subjects': []}), 500

@app.route('/api/get-students')
@login_required
def api_get_students():
    """API للحصول على جميع الطلاب"""
    try:
        students = get_all_students()
        if students is None:
            students = []
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        print(f'[API Error] api_get_students: {e}')
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}', 'students': []}), 500

# ============================================
# إعدادات النظام
# ============================================

import os
from werkzeug.utils import secure_filename

@app.route('/settings')
@login_required
def settings_page():
    """صفحة الإعدادات"""
    from database import get_settings, get_all_users
    settings = get_settings()
    
    # المستخدم العادي يشوف بس إعداداته، الـ admin يشوف الكل
    if session.get('username') == 'admin':
        users = get_all_users()
    else:
        users = []  # المستخدم العادي ما يشوف قائمة المستخدمين
    
    return render_template('settings.html', settings=settings, users=users, is_admin=(session.get('username') == 'admin'))


@app.route('/update-settings', methods=['POST'])
@login_required
@admin_required  # بس الـ admin يقدر يحدث الإعدادات العامة
def update_settings():
    """تحديث إعدادات النظام"""
    from database import get_settings, save_settings
    
    setting_type = request.form.get('setting_type')
    settings = get_settings()
    
    if setting_type == 'general':
        settings['dept_name'] = request.form.get('dept_name', 'قسم علوم الحاسوب')
        settings['dept_subtitle'] = request.form.get('dept_subtitle', 'نظام إدارة الحضور والغياب')
        
        # معالجة الصورة
        if 'dept_image' in request.files:
            file = request.files['dept_image']
            if file and file.filename:
                upload_dir = os.path.join('static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                filename = 'dept_logo.png'
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                settings['dept_image'] = '/static/uploads/' + filename
    
    save_settings(settings)
    flash('تم حفظ الإعدادات بنجاح!', 'success')
    return redirect(url_for('settings_page'))


@app.route('/add-user', methods=['POST'])
@login_required
@admin_required  # بس الـ admin يقدر يضيف مستخدمين
def add_user():
    """إضافة مستخدم جديد"""
    from database import add_new_user
    
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    if password != confirm_password:
        flash('كلمات المرور غير متطابقة!', 'error')
        return redirect(url_for('settings_page'))
    
    if len(password) < 6:
        flash('يجب أن تكون كلمة المرور 6 أحرف على الأقل!', 'error')
        return redirect(url_for('settings_page'))
    
    if add_new_user(username, password):
        flash(f'تم إضافة المستخدم {username} بنجاح!', 'success')
    else:
        flash('اسم المستخدم موجود مسبقاً!', 'error')
    
    return redirect(url_for('settings_page'))


@app.route('/delete-user/<username>', methods=['DELETE'])
@login_required
@admin_required  # بس الـ admin يقدر يحذف مستخدمين
def delete_user_route(username):
    """حذف مستخدم"""
    try:
        if username == session.get('username'):
            return jsonify({'success': False, 'message': 'لا يمكنك حذف حسابك الحالي!'})
        
        if username == 'admin':
            return jsonify({'success': False, 'message': 'لا يمكن حذف المستخدم الرئيسي!'})
        
        success = delete_user_by_username(username)
        if success:
            return jsonify({'success': True, 'message': 'تم حذف المستخدم بنجاح'})
        else:
            return jsonify({'success': False, 'message': 'فشل حذف المستخدم'}), 400
    except Exception as e:
        print(f'[API Error] delete_user: {e}')
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}'}), 500


@app.route('/change-password-admin', methods=['POST'])
@login_required
def change_password_admin():
    """تغيير كلمة المرور - أي مستخدم يقدر يغير كلمة مروره"""
    from database import change_user_password
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # التحقق من تطابق كلمات المرور
    if new_password != confirm_password:
        flash('كلمات المرور الجديدة غير متطابقة!', 'error')
        return redirect(url_for('settings_page'))
    
    if len(new_password) < 6:
        flash('يجب أن تكون كلمة المرور 6 أحرف على الأقل!', 'error')
        return redirect(url_for('settings_page'))
    
    # المستخدم يغير بس كلمة مروره، الـ admin يقدر يغير لأي شخص (اختياري)
    username = session.get('username')
    
    if change_user_password(username, current_password, new_password):
        flash('تم تغيير كلمة المرور بنجاح!', 'success')
    else:
        flash('كلمة المرور الحالية غير صحيحة!', 'error')
    
    return redirect(url_for('settings_page'))


if __name__ == '__main__':
    init_database()
    app.run(debug=False, host='0.0.0.0', port=5000)