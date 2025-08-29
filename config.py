import os

SECRET_KEY = os.environ.get("SECRET_KEY", "replace_this_with_random_secret")

# يمكنك إضافة وحذف المستخدمين حسب الحاجة
USERS = {
    'admin': {'password': 'admin', 'role': 'admin'},
    'employee': {'password': 'employee', 'role': 'employee'},
    'agent1': {'password': 'agent', 'role': 'agent'},
    'agent2': {'password': 'agent', 'role': 'agent'},
}

# اسم ملف قاعدة البيانات
DB_FILE = os.environ.get("DB_FILE", "orders_db.sqlite")