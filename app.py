from flask import Flask, request, render_template, redirect, url_for, session, flash, send_file, jsonify
import pandas as pd
import io
import traceback
from models import init_db, query_db, insert_orders_bulk, insert_users_bulk
from config import SECRET_KEY, USERS

app = Flask(__name__)
app.secret_key = SECRET_KEY

init_db()

insert_users_bulk([(user, USERS[user]['password'], USERS[user]['role']) for user in USERS])

@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = query_db('SELECT * FROM users WHERE username = ? AND password = ?', (username, password), one=True)
        
        if user_data:
            session['logged_in'] = True
            session['username'] = user_data['username']
            session['role'] = user_data['role']
            
            if session['role'] == 'admin' or session['role'] == 'employee':
                return redirect(url_for('index'))
            elif user_data['role'] == 'agent':
                return redirect(url_for('agent_dashboard'))
        else:
            flash("اسم المستخدم أو كلمة المرور خاطئة", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("تم تسجيل الخروج بنجاح", "success")
    return redirect(url_for('login'))

@app.route('/')
def index():
    if session.get('role') not in ['admin', 'employee']:
        flash("ليس لديك صلاحية الوصول لهذه الصفحة", "error")
        return redirect(url_for('login'))
        
    orders = query_db('SELECT * FROM orders ORDER BY id DESC')
    agents = [u for u in USERS if USERS[u]['role'] == 'agent']
    
    # حساب الإحصائيات الجديدة
    total_orders = len(orders)
    
    total_to_be_paid = 0
    delivered_full = 0
    delivered_partial = 0
    returns = 0
    
    for order in orders:
        status = order['status']
        price = order['price']
        received = order['received']
        shipping = order['shipping']
        
        # المبلغ المطلوب توريده
        if status in ['تم التسليم', 'تم التسليم جزئي']:
            total_to_be_paid += received
        # المرتجعات التي دفع العميل فيها الشحن
        elif status in ['ملغي', 'مرتجع'] and received > 0:
            total_to_be_paid += received
            
        # عدد الأوردرات المستلمة كاملة
        if status == 'تم التسليم':
            delivered_full += 1
        
        # عدد الأوردرات المستلمة جزئيا
        elif status == 'تم التسليم جزئي':
            delivered_partial += 1
            
        # عدد المرتجعات
        elif status in ['تم التأجيل', 'ملغي', 'مرتجع']:
            returns += 1
    
    return render_template('index.html',
                           orders=orders,
                           agents=agents,
                           total_orders=total_orders,
                           total_to_be_paid=total_to_be_paid,
                           delivered_full=delivered_full,
                           delivered_partial=delivered_partial,
                           returns=returns)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash("لم يتم اختيار ملف", "error")
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash("لم يتم اختيار ملف", "error")
        return redirect(url_for('index'))
    
    if file:
        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()
            
            data = []
            for index, row in df.iterrows():
                code = str(row.get('الكود', '')) if 'الكود' in df.columns else ''
                client_name = str(row.get('اسم العميل', '')) if 'اسم العميل' in df.columns else ''
                client_phone = str(row.get('رقم العميل', '')) if 'رقم العميل' in df.columns else ''
                address = str(row.get('العنوان', '')) if 'العنوان' in df.columns else ''
                sender = str(row.get('اسم الراسل', '')) if 'اسم الراسل' in df.columns else ''
                
                price_raw = row.get('سعر لاوردر', 0) if 'سعر لاوردر' in df.columns else 0
                try:
                    price = float(price_raw)
                except (ValueError, TypeError):
                    price = 0.0

                agent = str(row.get('اسم المندوب', '')) if 'اسم المندوب' in df.columns else ''
                status = str(row.get('الحاله', 'قيد التوصيل')) if 'الحاله' in df.columns else 'قيد التوصيل'
                
                province = ''
                notes = ''

                data.append((
                    code,
                    client_name,
                    client_phone,
                    province,
                    address,
                    sender,
                    price,
                    agent,
                    status,
                    notes
                ))
            
            insert_orders_bulk(data)
            flash("تم رفع الملف بنجاح", "success")
        except Exception as e:
            flash(f"حدث خطأ غير متوقع: {str(e)}", "error")
            traceback.print_exc()
    return redirect(url_for('index'))

@app.route('/add_order', methods=['POST'])
def add_order():
    code = request.form['code']
    client_name = request.form['clientName']
    client_phone = request.form['clientPhone']
    province = request.form['province']
    address = request.form['address']
    sender = request.form['sender']
    price = float(request.form['price'])
    agent = request.form['agent']
    status = request.form.get('status', 'قيد التوصيل')
    
    query_db('''
        INSERT INTO orders (code, clientName, clientPhone, province, address, sender, price, agent, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (code, client_name, client_phone, province, address, sender, price, agent, status))
    flash("تم إضافة الأوردر بنجاح", "success")
    return redirect(url_for('index'))

@app.route('/update_order', methods=['POST'])
def update_order():
    oid = request.form['id']
    received = float(request.form['received'])
    shipping = float(request.form['shipping'])
    status = request.form['status']
    notes = request.form['notes']
    
    query_db('''
        UPDATE orders SET received=?, shipping=?, status=?, notes=? WHERE id=?
    ''', (received, shipping, status, notes, oid))
    flash("تم تحديث الأوردر بنجاح", "success")
    return redirect(url_for('index'))

@app.route('/bulk_update', methods=['POST'])
def bulk_update():
    order_ids = request.form.getlist('order_ids[]')
    status = request.form.get('bulk_status')
    agent = request.form.get('bulk_agent')
    notes = request.form.get('bulk_note')
    
    for oid in order_ids:
        current_notes = query_db('SELECT notes FROM orders WHERE id=?', (oid,), one=True)['notes']
        new_notes = (current_notes + ' | ' + notes) if current_notes and notes else (current_notes or notes)
        
        query_db('''
            UPDATE orders SET status=?, agent=?, notes=? WHERE id=?
        ''', (status, agent, new_notes, oid))
        
    flash(f"تم تحديث {len(order_ids)} أوردر بنجاح", "success")
    return redirect(url_for('index'))

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    query_db('DELETE FROM orders WHERE id=?', (order_id,))
    flash("تم حذف الأوردر بنجاح", "success")
    return redirect(url_for('index'))

@app.route('/delete_all')
def delete_all():
    query_db('DELETE FROM orders')
    flash("تم حذف جميع الأوردرات بنجاح", "success")
    return redirect(url_for('index'))

@app.route('/export')
def export_orders():
    orders = query_db('SELECT * FROM orders')
    df = pd.DataFrame(orders, columns=orders[0].keys() if orders else [])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Orders")
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name='orders_export.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/agent')
def agent_dashboard():
    if session.get('role') != 'agent':
        flash("ليس لديك صلاحية الوصول لهذه الصفحة", "error")
        return redirect(url_for('login'))
        
    orders = query_db('SELECT * FROM orders WHERE agent = ? ORDER BY id DESC', (session.get('username'),))
    return render_template('agent_dashboard.html', orders=orders)

@app.route('/agent/update_status', methods=['POST'])
def agent_update_status():
    data = request.json
    order_id = data.get('order_id')
    status = data.get('status')
    collected = data.get('collected_price')
    notes = data.get('notes')
    
    if not order_id or not status:
        return jsonify({"success": False, "message": "بيانات غير مكتملة"}), 400

    query_db('''
        UPDATE orders SET status=?, received=?, notes=? WHERE id=?
    ''', (status, collected, notes, order_id))
    
    return jsonify({"success": True, "message": "تم تحديث الأوردر بنجاح"})