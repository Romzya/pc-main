from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'aboltus_key'

def init_db():
    conn = sqlite3.connect('db.db')
    c = conn.cursor()

    # Таблица пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            TP INTEGER NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')

    # Таблица сборок пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_gadjets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            Proc TEXT NOT NULL,
            MPlata TEXT NOT NULL,
            CW TEXT NOT NULL,
            RAM TEXT NOT NULL,
            VideoCard TEXT NOT NULL,
            BP TEXT NOT NULL,
            Corpus TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Таблица с комплектующими (обновленная с новыми полями)
    c.execute('''
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            price REAL DEFAULT 0,
            socket TEXT,
            memory_type TEXT,
            memory_speed INTEGER,
            memory_slots INTEGER
        )
    ''')
    
    # Таблица для чата по сборкам
    c.execute('''
        CREATE TABLE IF NOT EXISTS build_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            build_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (build_id) REFERENCES user_gadjets (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Таблица для статуса сборок
    c.execute('''
        CREATE TABLE IF NOT EXISTS build_status (
            build_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'active',
            needs_approval INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (build_id) REFERENCES user_gadjets (id)
        )
    ''')
    
    # Проверяем существование колонки is_admin
    try:
        c.execute("SELECT is_admin FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    
    # Проверяем и добавляем новые колонки в таблицу components
    try:
        c.execute("SELECT memory_type FROM components LIMIT 1")
    except sqlite3.OperationalError:
        # Добавляем колонки если они не существуют
        c.execute("ALTER TABLE components ADD COLUMN memory_type TEXT")
        c.execute("ALTER TABLE components ADD COLUMN memory_speed INTEGER")
        c.execute("ALTER TABLE components ADD COLUMN memory_slots INTEGER")
    
    # Проверяем существование администратора
    admin_check = c.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    if not admin_check:
        hashed_password = generate_password_hash('admin123')
        try:
            c.execute('''
                INSERT INTO users (username, password, TP, is_admin) 
                VALUES (?, ?, ?, ?)
            ''', ('admin', hashed_password, 1, 1))
        except sqlite3.IntegrityError:
            c.execute('''
                UPDATE users SET is_admin = 1 WHERE username = 'admin'
            ''')
    
    # Добавляем тестовые комплектующие, если таблица пуста
    components_check = c.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    if components_check == 0:
        test_components = [
    # ПРОЦЕССОРЫ INTEL LGA 1700 (только DDR4/DDR5 совместимы)
    ('Процессор', 'Intel Core i5-12400F', '6 ядер, 2.5-4.4 ГГц, LGA 1700', 12500, 'LGA 1700', '', 0, 0),
    ('Процессор', 'Intel Core i5-13400F', '10 ядер, 2.5-4.6 ГГц, LGA 1700', 15500, 'LGA 1700', '', 0, 0),
    ('Процессор', 'Intel Core i5-14400F', '10 ядер, 2.5-4.7 ГГц, LGA 1700', 17000, 'LGA 1700', '', 0, 0),
    ('Процессор', 'Intel Core i7-12700KF', '12 ядер, 3.6-5.0 ГГц, LGA 1700', 24000, 'LGA 1700', '', 0, 0),
    ('Процессор', 'Intel Core i7-13700KF', '16 ядер, 3.4-5.4 ГГц, LGA 1700', 28000, 'LGA 1700', '', 0, 0),
    ('Процессор', 'Intel Core i9-13900KF', '24 ядра, 3.0-5.8 ГГц, LGA 1700', 42000, 'LGA 1700', '', 0, 0),
    ('Процессор', 'Intel Core i9-14900KF', '24 ядра, 3.2-6.0 ГГц, LGA 1700', 48000, 'LGA 1700', '', 0, 0),
    
    # ПРОЦЕССОРЫ AMD AM4 (только DDR4)
    ('Процессор', 'AMD Ryzen 5 5600X', '6 ядер, 3.7-4.6 ГГц, AM4', 13500, 'AM4', '', 0, 0),
    ('Процессор', 'AMD Ryzen 5 5600G', '6 ядер, 3.9-4.4 ГГц, AM4', 12000, 'AM4', '', 0, 0),
    ('Процессор', 'AMD Ryzen 7 5700X', '8 ядер, 3.4-4.6 ГГц, AM4', 16500, 'AM4', '', 0, 0),
    ('Процессор', 'AMD Ryzen 7 5800X', '8 ядер, 3.8-4.7 ГГц, AM4', 18500, 'AM4', '', 0, 0),
    ('Процессор', 'AMD Ryzen 7 5800X3D', '8 ядер, 3.4-4.5 ГГц, AM4', 22000, 'AM4', '', 0, 0),
    ('Процессор', 'AMD Ryzen 9 5900X', '12 ядер, 3.7-4.8 ГГц, AM4', 26000, 'AM4', '', 0, 0),
    ('Процессор', 'AMD Ryzen 9 5950X', '16 ядер, 3.4-4.9 ГГц, AM4', 32000, 'AM4', '', 0, 0),
    
    # ПРОЦЕССОРЫ AMD AM5 (только DDR5)
    ('Процессор', 'AMD Ryzen 5 7600X', '6 ядер, 4.7-5.3 ГГц, AM5', 18500, 'AM5', '', 0, 0),
    ('Процессор', 'AMD Ryzen 5 7600', '6 ядер, 3.8-5.1 ГГц, AM5', 17000, 'AM5', '', 0, 0),
    ('Процессор', 'AMD Ryzen 7 7700X', '8 ядер, 4.5-5.4 ГГц, AM5', 23500, 'AM5', '', 0, 0),
    ('Процессор', 'AMD Ryzen 7 7700', '8 ядер, 3.8-5.3 ГГц, AM5', 21500, 'AM5', '', 0, 0),
    ('Процессор', 'AMD Ryzen 7 7800X3D', '8 ядер, 4.2-5.0 ГГц, AM5', 29000, 'AM5', '', 0, 0),
    ('Процессор', 'AMD Ryzen 9 7900X', '12 ядер, 4.7-5.6 ГГц, AM5', 34000, 'AM5', '', 0, 0),
    ('Процессор', 'AMD Ryzen 9 7950X3D', '16 ядер, 4.2-5.7 ГГц, AM5', 52000, 'AM5', '', 0, 0),
    
    # МАТЕРИНСКИЕ ПЛАТЫ INTEL LGA 1700 (DDR4 и DDR5 отдельно)
    ('Материнская плата', 'ASUS PRIME B760M-A DDR4', 'B760, LGA 1700, DDR4, mATX', 9500, 'LGA 1700', 'DDR4', 3200, 4),
    ('Материнская плата', 'ASUS PRIME B760M-A DDR5', 'B760, LGA 1700, DDR5, mATX', 10500, 'LGA 1700', 'DDR5', 5600, 4),
    ('Материнская плата', 'Gigabyte B760M GAMING X DDR4', 'B760, LGA 1700, DDR4, mATX', 10000, 'LGA 1700', 'DDR4', 3200, 4),
    ('Материнская плата', 'Gigabyte B760M GAMING X DDR5', 'B760, LGA 1700, DDR5, mATX', 11000, 'LGA 1700', 'DDR5', 6000, 4),
    ('Материнская плата', 'MSI MAG B760 TOMAHAWK DDR4', 'B760, LGA 1700, DDR4, ATX', 13000, 'LGA 1700', 'DDR4', 3200, 4),
    ('Материнская плата', 'MSI MAG B760 TOMAHAWK DDR5', 'B760, LGA 1700, DDR5, ATX', 14500, 'LGA 1700', 'DDR5', 6400, 4),
    ('Материнская плата', 'ASUS ROG STRIX Z790-F DDR5', 'Z790, LGA 1700, DDR5, ATX', 28000, 'LGA 1700', 'DDR5', 6400, 4),
    ('Материнская плата', 'Gigabyte Z790 AORUS ELITE DDR5', 'Z790, LGA 1700, DDR5, ATX', 22000, 'LGA 1700', 'DDR5', 6400, 4),
    
    # МАТЕРИНСКИЕ ПЛАТЫ AM4 (DDR4)
    ('Материнская плата', 'ASUS ROG STRIX X570-E GAMING', 
     'X570, AM4, DDR4, ATX', 21000, 'AM4', 'DDR4', 3200, 4),
    
    ('Материнская плата', 'ASUS TUF GAMING B550-PLUS', 
     'B550, AM4, DDR4, ATX', 10500, 'AM4', 'DDR4', 3200, 4),
    
     # МАТЕРИНСКИЕ ПЛАТЫ AM5 (DDR5)
    ('Материнская плата', 'ASUS TUF GAMING B650-PLUS', 
     'B650, AM5, DDR5, ATX', 16000, 'AM5', 'DDR5', 6000, 4),
    
    # СИСТЕМЫ ОХЛАЖДЕНИЯ (универсальные)
    ('Система охлаждения', 'ID-COOLING SE-214-XT', 'Башенный, 120мм, до 150W', 1800, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'DeepCool AG400', 'Башенный, 120мм, до 220W', 2200, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'DeepCool AK400', 'Башенный, 120мм, до 220W', 2800, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'DeepCool AK620', 'Двойной вентилятор, до 240W', 4500, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'Noctua NH-U12A', 'Премиальный, 120мм', 8500, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'Noctua NH-D15', 'Флагманский, двойной вентилятор', 10500, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'Corsair iCUE H100i RGB', 'СВО 240мм, ARGB', 11500, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'Arctic Liquid Freezer II 240', 'СВО 240мм', 7500, 'LGA 1700/AM4/AM5', '', 0, 0),
    ('Система охлаждения', 'NZXT Kraken X63', 'СВО 280мм, RGB', 13500, 'LGA 1700/AM4/AM5', '', 0, 0),
    
    # ОПЕРАТИВНАЯ ПАМЯТЬ DDR4
    ('Оперативная память', 'Corsair Vengeance LPX 32GB DDR4 3200МГц', 
     '32GB DDR4 3200МГц, CL16, 2x16GB', 6500, '', 'DDR4', 3200, 2),
    
    ('Оперативная память', 'Kingston FURY Beast 32GB DDR4 3200МГц', 
     '32GB DDR4 3200МГц, CL16, 2x16GB', 6500, '', 'DDR4', 3200, 2),
    
    # ОПЕРАТИВНАЯ ПАМЯТЬ DDR5
    ('Оперативная память', 'Kingston FURY Beast 32GB DDR5 5600МГц', 
     '32GB DDR5 5600МГц, CL36, 2x16GB', 8500, '', 'DDR5', 5600, 2),
    
    
    # ВИДЕОКАРТЫ NVIDIA (универсальные)
    ('Видеокарта', 'NVIDIA GeForce RTX 4060 8GB', 'AD107, 3072 ядра, 1830 МГц', 32000, '', '', 0, 0),
    ('Видеокарта', 'NVIDIA GeForce RTX 4060 Ti 8GB', 'AD106, 4352 ядра, 2310 МГц', 38000, '', '', 0, 0),
    ('Видеокарта', 'NVIDIA GeForce RTX 4060 Ti 16GB', 'AD106, 4352 ядра, 2310 МГц', 42000, '', '', 0, 0),
    ('Видеокарта', 'NVIDIA GeForce RTX 4070 12GB', 'AD104, 5888 ядер, 1920 МГц', 52000, '', '', 0, 0),
    ('Видеокарта', 'NVIDIA GeForce RTX 4070 SUPER 12GB', 'AD104, 7168 ядер, 1980 МГц', 58000, '', '', 0, 0),
    ('Видеокарта', 'NVIDIA GeForce RTX 4070 Ti SUPER 16GB', 'AD103, 8448 ядер, 2340 МГц', 72000, '', '', 0, 0),
    ('Видеокарта', 'NVIDIA GeForce RTX 4080 SUPER 16GB', 'AD103, 10240 ядер, 2295 МГц', 98000, '', '', 0, 0),
    ('Видеокарта', 'NVIDIA GeForce RTX 4090 24GB', 'AD102, 16384 ядра, 2235 МГц', 165000, '', '', 0, 0),
    
    # ВИДЕОКАРТЫ AMD (универсальные)
    ('Видеокарта', 'AMD Radeon RX 7600 8GB', 'Navi 33, 2048 ядер, 2250 МГц', 28000, '', '', 0, 0),
    ('Видеокарта', 'AMD Radeon RX 7700 XT 12GB', 'Navi 32, 3456 ядер, 2100 МГц', 42000, '', '', 0, 0),
    ('Видеокарта', 'AMD Radeon RX 7800 XT 16GB', 'Navi 32, 3840 ядер, 2124 МГц', 48000, '', '', 0, 0),
    ('Видеокарта', 'AMD Radeon RX 7900 GRE 16GB', 'Navi 31, 5120 ядер, 1880 МГц', 55000, '', '', 0, 0),
    ('Видеокарта', 'AMD Radeon RX 7900 XT 20GB', 'Navi 31, 5376 ядер, 1900 МГц', 68000, '', '', 0, 0),
    ('Видеокарта', 'AMD Radeon RX 7900 XTX 24GB', 'Navi 31, 6144 ядра, 1900 МГц', 85000, '', '', 0, 0),
    
    # БЛОКИ ПИТАНИЯ (универсальные)
    ('Блок питания', 'AeroCool VX PLUS 500W', '500W, 80+ Bronze', 2500, '', '', 0, 0),
    ('Блок питания', 'Be quiet! System Power 9 600W', '600W, 80+ Bronze', 3500, '', '', 0, 0),
    ('Блок питания', 'Cooler Master MWE Bronze 650W', '650W, 80+ Bronze', 4000, '', '', 0, 0),
    ('Блок питания', 'DeepCool PF650 650W', '650W, 80+ Bronze', 3800, '', '', 0, 0),
    ('Блок питания', 'Corsair CV650 650W', '650W, 80+ Bronze', 4500, '', '', 0, 0),
    ('Блок питания', 'Corsair RM750e 750W', '750W, 80+ Gold', 7500, '', '', 0, 0),
    ('Блок питания', 'Be quiet! Pure Power 11 700W', '700W, 80+ Gold', 8500, '', '', 0, 0),
    ('Блок питания', 'Seasonic FOCUS GX-850', '850W, 80+ Gold', 9500, '', '', 0, 0),
    ('Блок питания', 'Corsair RM850x 850W', '850W, 80+ Gold', 10500, '', '', 0, 0),
    ('Блок питания', 'Thermaltake Toughpower GF3 1000W', '1000W, 80+ Gold, ATX 3.0', 13500, '', '', 0, 0),
    ('Блок питания', 'MSI MPG A1000G PCIE5', '1000W, 80+ Gold, ATX 3.0', 14500, '', '', 0, 0),
    ('Блок питания', 'Seasonic VERTEX GX-1200', '1200W, 80+ Gold, ATX 3.0', 19500, '', '', 0, 0),
    
    # КОРПУСА (универсальные)
    ('Корпус', 'DeepCool MATREXX 40', 'mATX, стеклянная боковая', 2500, '', '', 0, 0),
    ('Корпус', 'Zalman S2', 'ATX, меш-фасад', 3000, '', '', 0, 0),
    ('Корпус', 'AeroCool Cylon', 'ATX, RGB фронтальная панель', 3500, '', '', 0, 0),
    ('Корпус', 'DeepCool MATREXX 55 MESH', 'ATX, меш-фасад, стекло', 4500, '', '', 0, 0),
    ('Корпус', 'Fractal Design Pop Air', 'ATX, меш-фасад, RGB', 6500, '', '', 0, 0),
    ('Корпус', 'NZXT H5 Flow', 'ATX, меш-фасад, вентиляторы', 7500, '', '', 0, 0),
    ('Корпус', 'Lian Li Lancool 216', 'ATX, меш-фасад, 2x160мм вентиляторы', 8500, '', '', 0, 0),
    ('Корпус', 'Corsair 4000D AIRFLOW', 'ATX, меш-фасад, премиум', 9000, '', '', 0, 0),
    ('Корпус', 'be quiet! Pure Base 500DX', 'ATX, меш-фасад, шумоизоляция', 9500, '', '', 0, 0),
    ('Корпус', 'Phanteks Eclipse G360A', 'ATX, меш-фасад, 3xARGB вентиляторы', 8000, '', '', 0, 0),
    ('Корпус', 'Fractal Design North', 'ATX, деревянная отделка, меш', 12000, '', '', 0, 0),
    ('Корпус', 'Lian Li O11 Dynamic EVO', 'E-ATX, двойная камера, RGB', 15000, '', '', 0, 0),
    ('Корпус', 'NZXT H9 Flow', 'Двойная камера, панорамное стекло', 16000, '', '', 0, 0),
    ('Корпус', 'HYTE Y60', 'Угловое панорамное стекло', 18000, '', '', 0, 0),
    ('Корпус', 'Corsair 5000D AIRFLOW', 'Премиальный, максимальная вентиляция', 14000, '', '', 0, 0),
]
        
        for component in test_components:
            try:
                c.execute('''
                    INSERT INTO components (category, name, description, price, socket, memory_type, memory_speed, memory_slots)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', component)
            except sqlite3.IntegrityError:
                pass
    else:
        # Обновляем существующие записи если нужно
        # Можно добавить код для обновления старых записей здесь
        pass
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('db.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_socket_compatibility_simple(processor_name, motherboard_name):
    """
    Улучшенная проверка совместимости через БД
    """
    conn = get_db_connection()
    
    # Получаем socket процессора
    cpu = conn.execute(
        'SELECT socket FROM components WHERE name = ? AND category = "Процессор"',
        (processor_name,)
    ).fetchone()
    
    # Получаем socket материнской платы
    mb = conn.execute(
        'SELECT socket FROM components WHERE name = ? AND category = "Материнская плата"',
        (motherboard_name,)
    ).fetchone()
    
    conn.close()
    
    if not cpu:
        return False, "Процессор не найден в базе данных"
    
    if not mb:
        return False, "Материнская плата не найдена в базе данных"
    
    cpu_socket = (cpu['socket'] or '').upper().strip()
    mb_socket = (mb['socket'] or '').upper().strip()
    
    if not cpu_socket:
        return False, "ОШИБКА: Сокет процессора не указан в базе"
    
    if not mb_socket:
        return False, "ОШИБКА: Сокет материнской платы не указан в базе"
    
    # Проверяем совместимость
    if cpu_socket == mb_socket:
        return True, f"✓ Отлично! Сокеты совпадают: {cpu_socket}"
    
    # Проверяем совместимость Intel (LGA1700)
    if 'LGA 1700' in cpu_socket and 'LGA 1700' in mb_socket:
        return True, f"✓ Совместимо: LGA 1700"
    
    # Проверяем совместимость AMD
    if 'AM4' in cpu_socket and 'AM4' in mb_socket:
        return True, f"✓ Совместимо: AM4"
    
    if 'AM5' in cpu_socket and 'AM5' in mb_socket:
        return True, f"✓ Совместимо: AM5"
    
    # НЕСОВМЕСТИМОСТЬ
    return False, f"❌ НЕСОВМЕСТИМО! Процессор ({cpu_socket}) не подходит к материнской плате ({mb_socket})"

def check_memory_compatibility(motherboard_name, ram_name):
    """Проверка совместимости оперативной памяти"""
    conn = get_db_connection()
    
    # Получаем информацию о материнской плате
    mb = conn.execute(
        'SELECT memory_type, memory_speed FROM components WHERE name = ? AND category = "Материнская плата"',
        (motherboard_name,)
    ).fetchone()
    
    # Получаем информацию об оперативной памяти
    ram = conn.execute(
        'SELECT memory_type, memory_speed FROM components WHERE name = ? AND category = "Оперативная память"',
        (ram_name,)
    ).fetchone()
    
    conn.close()
    
    if not mb:
        return False, "ОШИБКА: Материнская плата не найдена"
    
    if not ram:
        return False, "ОШИБКА: Оперативная память не найдена"
    
    mb_memory_type = mb['memory_type'] or ''
    ram_memory_type = ram['memory_type'] or ''
    mb_memory_speed = mb['memory_speed'] or 0
    ram_memory_speed = ram['memory_speed'] or 0
    
    if not mb_memory_type:
        return False, "❌ ОШИБКА: Тип памяти материнской платы не указан в базе"
    
    if not ram_memory_type:
        return False, "❌ ОШИБКА: Тип памяти оперативной памяти не указан в базе"
    
    # Проверяем тип памяти
    if mb_memory_type != ram_memory_type:
        return False, f"❌ НЕСОВМЕСТИМО! Материнская плата поддерживает {mb_memory_type}, а память - {ram_memory_type}"
    
    # Проверяем скорость (память может быть быстрее, чем поддерживает мат. плата)
    if ram_memory_speed > mb_memory_speed > 0:
        return True, f"⚠️ Внимание: Память {ram_memory_speed}МГц будет работать на {mb_memory_speed}МГц (макс. для платы)"
    
    return True, f"✓ Совместимо: {ram_memory_type} {ram_memory_speed}МГц"

def is_admin():
    """Проверка, является ли пользователь администратором"""
    if 'user_id' not in session:
        return False
    
    conn = get_db_connection()
    user = conn.execute('SELECT is_admin FROM users WHERE id = ?', 
                       (session['user_id'],)).fetchone()
    conn.close()
    
    return user and user['is_admin'] == 1

def get_build_status(build_id):
    """Получение статуса сборки"""
    conn = get_db_connection()
    status = conn.execute('SELECT * FROM build_status WHERE build_id = ?', (build_id,)).fetchone()
    conn.close()
    
    if status:
        return dict(status)
    return {'needs_approval': 0, 'status': 'active'}

@app.context_processor
def utility_processor():
    """Добавляем функции в контекст всех шаблонов"""
    return dict(get_build_status=get_build_status)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Получаем все компоненты, сгруппированные по категориям
    all_components = conn.execute('''
        SELECT category, name, description, price, socket, 
               memory_type, memory_speed, memory_slots,
               COALESCE(power_consumption, tdp, 0) as power
        FROM components 
        ORDER BY category, name
    ''').fetchall()
    
    # Группируем компоненты по категориям
    components_by_category = {}
    for comp in all_components:
        category = comp['category']
        if category not in components_by_category:
            components_by_category[category] = []
        
        components_by_category[category].append({
            'name': comp['name'],
            'description': comp['description'],
            'price': comp['price'],
            'socket': comp['socket'],
            'memory_type': comp['memory_type'],
            'memory_speed': comp['memory_speed'],
            'memory_slots': comp['memory_slots'],
            'power': comp['power']  # Добавляем мощность
        })
    
    # Получаем сборки пользователя
    passwords = conn.execute('''
        SELECT * FROM user_gadjets 
        WHERE user_id = ? 
        ORDER BY id DESC
    ''', (session['user_id'],)).fetchall()
    
    # Рассчитываем цены и мощность для каждой сборки
    builds_with_prices = []
    total_user_price = 0
    total_user_power = 0
    
    for build in passwords:
        build_dict = dict(build)
        build_price = 0
        build_power = 0
        
        # Рассчитываем цену и мощность для каждой сборки
        components_to_check = [
            ('Процессор', build['Proc']),
            ('Материнская плата', build['MPlata']),
            ('Система охлаждения', build['CW']),
            ('Оперативная память', build['RAM']),
            ('Видеокарта', build['VideoCard']),
            ('Блок питания', build['BP']),
            ('Корпус', build['Corpus'])
        ]
        
        for category, name in components_to_check:
            result = conn.execute(
                '''SELECT price, COALESCE(power_consumption, tdp, 0) as power 
                   FROM components WHERE category = ? AND name = ?''',
                (category, name)
            ).fetchone()
            
            if result:
                if result['price']:
                    build_price += float(result['price'])
                if result['power']:
                    try:
                        build_power += int(result['power'])
                    except (ValueError, TypeError):
                        pass
        
        build_dict['total_price'] = build_price
        build_dict['total_power'] = build_power
        builds_with_prices.append(build_dict)
        total_user_price += build_price
        total_user_power += build_power
    
    conn.close()
    
    return render_template('index.html', 
                         passwords=builds_with_prices,
                         username=session['username'],
                         is_admin=is_admin(),
                         total_user_price=total_user_price,
                         total_user_power=total_user_power,
                         components_by_category=components_by_category)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        TP = request.form['TP']
        
        if username and password:
            conn = get_db_connection()
            try:
                hashed_password = generate_password_hash(password)
                conn.execute('INSERT INTO users (username, password, TP) VALUES (?, ?, ?)',
                           (username, hashed_password, TP))
                conn.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                error = 'Пользователь с таким именем уже существует'
                return render_template('register.html', error=error)
            finally:
                conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            error = 'Неверное имя пользователя или пароль'
            return render_template('login.html', error=error)
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
def add_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    Proc = request.form['Proc']
    MPlata = request.form['MPlata']
    CW = request.form['CW']
    RAM = request.form['RAM']
    VideoCard = request.form['VideoCard']
    BP = request.form['BP']
    Corpus = request.form['Corpus']
    
    if Proc and MPlata and CW and RAM and VideoCard and BP and Corpus:
        # Проверка совместимости сокетов
        is_cpu_compatible, cpu_message = check_socket_compatibility_simple(Proc, MPlata)
        
        if not is_cpu_compatible:
            flash(f'ОШИБКА совместимости: {cpu_message}', 'error')
            return redirect(url_for('index'))
        
        # Проверка совместимости памяти
        is_mem_compatible, mem_message = check_memory_compatibility(MPlata, RAM)
        
        if not is_mem_compatible:
            flash(f'ОШИБКА совместимости памяти: {mem_message}', 'error')
            return redirect(url_for('index'))
        
        # Проверка мощности БП
        build_dict = {
            'Proc': Proc,
            'MPlata': MPlata,
            'CW': CW,
            'RAM': RAM,
            'VideoCard': VideoCard,
            'BP': BP,
            'Corpus': Corpus
        }
        
        total_power = calculate_build_power_consumption(build_dict)
        required_psu = calculate_required_psu_wattage(build_dict)
        
        # Получаем мощность выбранного БП из базы
        conn = get_db_connection()
        psu_result = conn.execute(
            'SELECT name FROM components WHERE category = "Блок питания" AND name = ?',
            (BP,)
        ).fetchone()
        conn.close()
        
        # Извлекаем мощность из названия БП
        psu_power = 0
        if psu_result:
            import re
            psu_name = psu_result['name']
            # Ищем число с W или Вт в названии
            match = re.search(r'(\d+)\s*(W|Вт|watt|ватт)', psu_name, re.IGNORECASE)
            if match:
                psu_power = int(match.group(1))
        
        if psu_power and psu_power < required_psu:
            flash(f'⚠️ Внимание! Выбранный БП {BP} ({psu_power}W) может быть недостаточен. '
                  f'Рекомендуется БП от {required_psu}W. '
                  f'Потребление сборки: ~{total_power}W', 'warning')
        elif total_power > 0:
            flash(f'✓ Сборка создана! Потребление: ~{total_power}W. '
                  f'Рекомендуемый БП: {required_psu}W', 'success')
        
        conn = get_db_connection()
        cursor = conn.execute('''
            INSERT INTO user_gadjets (user_id, Proc, MPlata, CW, RAM, VideoCard, BP, Corpus) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], Proc, MPlata, CW, RAM, VideoCard, BP, Corpus))
        build_id = cursor.lastrowid
        
        # Добавляем сообщение в чат
        conn.execute('''
            INSERT INTO build_chat (build_id, user_id, message, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (build_id, session['user_id'], f'Сборка создана. Расчетная мощность: {total_power}W', 0))
        
        conn.commit()
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/delete/<int:password_id>')
def delete_password(password_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if is_admin():
        # Администратор может удалять любую запись
        conn.execute('DELETE FROM user_gadjets WHERE id = ?', (password_id,))
        conn.execute('DELETE FROM build_chat WHERE build_id = ?', (password_id,))
        conn.execute('DELETE FROM build_status WHERE build_id = ?', (password_id,))
    else:
        # Обычный пользователь может удалять только свои записи
        conn.execute('DELETE FROM user_gadjets WHERE id = ? AND user_id = ?', 
                    (password_id, session['user_id']))
        conn.execute('DELETE FROM build_chat WHERE build_id = ?', (password_id,))
        conn.execute('DELETE FROM build_status WHERE build_id = ?', (password_id,))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/admin')
def admin_panel():
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    all_gadjets = conn.execute('''
        SELECT 
            ug.id,
            ug.Proc,
            ug.MPlata,
            ug.CW,
            ug.RAM,
            ug.VideoCard,
            ug.BP,
            ug.Corpus,
            u.username,
            u.TP
        FROM user_gadjets ug
        JOIN users u ON ug.user_id = u.id
        ORDER BY u.username, ug.id
    ''').fetchall()
    
    # Функция для расчета цены сборки
    def calculate_build_price(build):
        total_price = 0
        components_to_check = [
            ('Процессор', build['Proc']),
            ('Материнская плата', build['MPlata']),
            ('Система охлаждения', build['CW']),
            ('Оперативная память', build['RAM']),
            ('Видеокарта', build['VideoCard']),
            ('Блок питания', build['BP']),
            ('Корпус', build['Corpus'])
        ]
        
        for category, name in components_to_check:
            price_result = conn.execute(
                'SELECT price FROM components WHERE category = ? AND name = ?',
                (category, name)
            ).fetchone()
            
            if price_result and price_result['price']:
                total_price += float(price_result['price'])
        
        return total_price
    
    # Рассчитываем цены для каждой сборки
    builds_with_prices = []
    total_all_builds_price = 0
    
    for build in all_gadjets:
        build_dict = dict(build)
        build_price = calculate_build_price(build_dict)
        build_dict['total_price'] = build_price
        builds_with_prices.append(build_dict)
        total_all_builds_price += build_price
    
    # Получаем все комплектующие для выпадающих списков
    all_components = conn.execute('''
        SELECT DISTINCT category, name 
        FROM components 
        ORDER BY category, name
    ''').fetchall()
    
    # Группируем комплектующие по категориям
    components_by_category = {}
    for comp in all_components:
        category = comp['category']
        if category not in components_by_category:
            components_by_category[category] = []
        components_by_category[category].append(comp['name'])
    
    stats = conn.execute('''
        SELECT 
            COUNT(DISTINCT u.id) as total_users,
            COUNT(ug.id) as total_gadjets,
            AVG(u.TP) as avg_tp
        FROM users u
        LEFT JOIN user_gadjets ug ON u.id = ug.user_id
        WHERE u.is_admin = 0
    ''').fetchone()
    
    conn.close()
    
    stats_dict = dict(stats)
    stats_dict['total_price'] = total_all_builds_price
    
    return render_template('admin.html',
                         all_gadjets=builds_with_prices,
                         stats=stats_dict,
                         username=session['username'],
                         components_by_category=components_by_category)

@app.route('/admin/edit/<int:build_id>', methods=['GET', 'POST'])
def edit_build(build_id):
    """Редактирование сборки (только для админа)"""
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Получаем данные из формы
        Proc = request.form['Proc']
        MPlata = request.form['MPlata']
        CW = request.form['CW']
        RAM = request.form['RAM']
        VideoCard = request.form['VideoCard']
        BP = request.form['BP']
        Corpus = request.form['Corpus']
        
        # Получаем старые данные для сравнения
        old_build = conn.execute('SELECT * FROM user_gadjets WHERE id = ?', (build_id,)).fetchone()
        old_build_dict = dict(old_build) if old_build else {}
        
        # Сравниваем изменения
        changes = []
        if old_build_dict.get('Proc') != Proc:
            changes.append(f"Процессор: {old_build_dict.get('Proc', '')} → {Proc}")
        if old_build_dict.get('MPlata') != MPlata:
            changes.append(f"Материнская плата: {old_build_dict.get('MPlata', '')} → {MPlata}")
        if old_build_dict.get('CW') != CW:
            changes.append(f"Система охлаждения: {old_build_dict.get('CW', '')} → {CW}")
        if old_build_dict.get('RAM') != RAM:
            changes.append(f"ОЗУ: {old_build_dict.get('RAM', '')} → {RAM}")
        if old_build_dict.get('VideoCard') != VideoCard:
            changes.append(f"Видеокарта: {old_build_dict.get('VideoCard', '')} → {VideoCard}")
        if old_build_dict.get('BP') != BP:
            changes.append(f"БП: {old_build_dict.get('BP', '')} → {BP}")
        if old_build_dict.get('Corpus') != Corpus:
            changes.append(f"Корпус: {old_build_dict.get('Corpus', '')} → {Corpus}")
        
        # Обновляем сборку
        conn.execute('''
            UPDATE user_gadjets 
            SET Proc = ?, MPlata = ?, CW = ?, RAM = ?, VideoCard = ?, BP = ?, Corpus = ?
            WHERE id = ?
        ''', (Proc, MPlata, CW, RAM, VideoCard, BP, Corpus, build_id))
        
        # Добавляем сообщение в чат об изменениях
        if changes:
            changes_text = "\n".join(changes)
            conn.execute('''
                INSERT INTO build_chat (build_id, user_id, message, is_admin)
                VALUES (?, ?, ?, ?)
            ''', (build_id, session['user_id'], f"📝 Администратор внес изменения:\n{changes_text}", 1))
        
        # Сбрасываем статус "нужно согласование" после редактирования
        conn.execute('''
            INSERT OR REPLACE INTO build_status (build_id, needs_approval, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (build_id, 0))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_panel'))
    
    # GET запрос - показываем форму редактирования
    build = conn.execute('SELECT * FROM user_gadjets WHERE id = ?', (build_id,)).fetchone()
    
    if not build:
        conn.close()
        return redirect(url_for('admin_panel'))
    
    # Получаем все комплектующие для выпадающих списков
    all_components = conn.execute('''
        SELECT DISTINCT category, name 
        FROM components 
        ORDER BY category, name
    ''').fetchall()
    
    # Группируем комплектующие по категориям
    components_by_category = {}
    for comp in all_components:
        category = comp['category']
        if category not in components_by_category:
            components_by_category[category] = []
        components_by_category[category].append(comp['name'])
    
    conn.close()
    
    if not build:
        return redirect(url_for('admin_panel'))
    
    build_dict = dict(build)
    
    return render_template('edit_build.html',
                         build=build_dict,
                         components_by_category=components_by_category,
                         username=session['username'])

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    """Удаление пользователя и всех его сборок (только для админа)"""
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Не позволяем удалить самого себя
    if user_id != session['user_id']:
        # Удаляем все сборки пользователя
        conn.execute('DELETE FROM user_gadjets WHERE user_id = ?', (user_id,))
        # Удаляем все сообщения чата пользователя
        conn.execute('DELETE FROM build_chat WHERE user_id = ?', (user_id,))
        # Удаляем пользователя
        conn.execute('DELETE FROM users WHERE id = ? AND is_admin = 0', (user_id,))
        conn.commit()
    
    conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/users')
def admin_users():
    """Список всех пользователей (только для админа)"""
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    users = conn.execute('''
        SELECT u.id, u.username, u.TP, u.is_admin,
               COUNT(ug.id) as build_count
        FROM users u
        LEFT JOIN user_gadjets ug ON u.id = ug.user_id
        GROUP BY u.id
        ORDER BY u.username
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin_users.html',
                         users=users,
                         username=session['username'])

@app.route('/api/components/<category>')
def get_components_by_category(category):
    """API для получения комплектующих по категории"""
    conn = get_db_connection()
    components = conn.execute('''
        SELECT id, name, description, price, socket, memory_type, memory_speed, memory_slots 
        FROM components 
        WHERE category = ?
        ORDER BY name
    ''', (category,)).fetchall()
    conn.close()
    
    components_list = []
    for component in components:
        components_list.append({
            'id': component['id'],
            'name': component['name'],
            'description': component['description'],
            'price': component['price'],
            'socket': component['socket'],
            'memory_type': component['memory_type'],
            'memory_speed': component['memory_speed'],
            'memory_slots': component['memory_slots']
        })
    
    return jsonify(components_list)

@app.route('/api/components')
def get_all_components():
    """API для получения всех комплектующих"""
    conn = get_db_connection()
    components = conn.execute('''
        SELECT category, name, description, price, socket, memory_type, memory_speed, memory_slots 
        FROM components 
        ORDER BY category, name
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(comp) for comp in components])

@app.route('/admin/components', methods=['GET', 'POST'])
def manage_components_page():
    """Страница управления комплектующими (только для админа)"""
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        category = request.form['category']
        name = request.form['name']
        description = request.form.get('description', '')
        price_str = request.form.get('price', '0')
        socket = request.form.get('socket', '')
        memory_type = request.form.get('memory_type', '')
        memory_speed = request.form.get('memory_speed', '0')
        memory_slots = request.form.get('memory_slots', '1')
        
        try:
            price = float(price_str) if price_str else 0.0
            mem_speed = int(memory_speed) if memory_speed else 0
            mem_slots = int(memory_slots) if memory_slots else 1
        except ValueError:
            price = 0.0
            mem_speed = 0
            mem_slots = 1
        
        try:
            conn.execute('''
                INSERT OR REPLACE INTO components (category, name, description, price, socket, memory_type, memory_speed, memory_slots)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (category, name, description, price, socket, memory_type, mem_speed, mem_slots))
            conn.commit()
        except sqlite3.IntegrityError as e:
            print(f"Ошибка добавления компонента: {e}")
        
        return redirect(url_for('manage_components_page'))
    
    # GET запрос - показываем список компонентов
    components = conn.execute('SELECT * FROM components ORDER BY category, name').fetchall()
    conn.close()
    
    return render_template('manage_components.html',
                         components=components,
                         username=session.get('username', 'Администратор'))

@app.route('/admin/components/delete/<int:component_id>')
def delete_component_by_id(component_id):
    """Удаление комплектующего (только для админа)"""
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM components WHERE id = ?', (component_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('manage_components_page'))

# ЧАТ СИСТЕМА
@app.route('/chat/build/<int:build_id>')
def build_chat(build_id):
    """Чат по конкретной сборке"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Проверяем доступ к сборке
    build = conn.execute('''
        SELECT ug.*, u.username 
        FROM user_gadjets ug
        JOIN users u ON ug.user_id = u.id
        WHERE ug.id = ?
    ''', (build_id,)).fetchone()
    
    if not build:
        conn.close()
        return redirect(url_for('index'))
    
    # Проверяем права доступа
    build_dict = dict(build)
    user_can_access = (session['user_id'] == build_dict['user_id']) or is_admin()
    
    if not user_can_access:
        conn.close()
        return redirect(url_for('index'))
    
    # Получаем сообщения чата
    messages = conn.execute('''
        SELECT bc.*, u.username 
        FROM build_chat bc
        JOIN users u ON bc.user_id = u.id
        WHERE bc.build_id = ?
        ORDER BY bc.created_at ASC
    ''', (build_id,)).fetchall()
    
    # Получаем статус сборки
    status = conn.execute('SELECT * FROM build_status WHERE build_id = ?', (build_id,)).fetchone()
    
    # Преобразуем статус в словарь или создаем дефолтный
    if status:
        status_dict = dict(status)
    else:
        status_dict = {'needs_approval': 0, 'status': 'active'}
    
    conn.close()
    
    return render_template('build_chat.html',
                         build=build_dict,
                         messages=messages,
                         status=status_dict,
                         username=session['username'],
                         is_admin=is_admin(),
                         user_id=session['user_id'])

@app.route('/admin/components/update', methods=['POST'])
def update_component():
    """Обновление комплектующего (только для админа)"""
    if not is_admin():
        return redirect(url_for('index'))
    
    component_id = request.form.get('id')
    category = request.form.get('category')
    name = request.form.get('name')
    description = request.form.get('description', '')
    price_str = request.form.get('price', '0')
    socket = request.form.get('socket', '')
    memory_type = request.form.get('memory_type', '')
    memory_speed = request.form.get('memory_speed', '0')
    memory_slots = request.form.get('memory_slots', '1')
    
    try:
        price = float(price_str) if price_str else 0.0
        mem_speed = int(memory_speed) if memory_speed else 0
        mem_slots = int(memory_slots) if memory_slots else 1
    except ValueError:
        price = 0.0
        mem_speed = 0
        mem_slots = 1
    
    if component_id and category and name:
        conn = get_db_connection()
        conn.execute('''
            UPDATE components 
            SET category = ?, name = ?, description = ?, price = ?, socket = ?,
                memory_type = ?, memory_speed = ?, memory_slots = ?
            WHERE id = ?
        ''', (category, name, description, price, socket, 
              memory_type, mem_speed, mem_slots, component_id))
        conn.commit()
        conn.close()
    
    return redirect(url_for('manage_components_page'))

@app.route('/chat/build/<int:build_id>/send', methods=['POST'])
def send_chat_message(build_id):
    """Отправка сообщения в чат сборки"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    message = request.form.get('message', '').strip()
    
    if not message:
        return redirect(url_for('build_chat', build_id=build_id))
    
    conn = get_db_connection()
    
    # Проверяем доступ к сборке
    build = conn.execute('SELECT * FROM user_gadjets WHERE id = ?', (build_id,)).fetchone()
    
    if not build:
        conn.close()
        return redirect(url_for('index'))
    
    build_dict = dict(build)
    user_can_access = (session['user_id'] == build_dict['user_id']) or is_admin()
    
    if not user_can_access:
        conn.close()
        return redirect(url_for('index'))
    
    # Отправляем сообщение
    conn.execute('''
        INSERT INTO build_chat (build_id, user_id, message, is_admin)
        VALUES (?, ?, ?, ?)
    ''', (build_id, session['user_id'], message, 1 if is_admin() else 0))
    
    # Обновляем статус если это администратор
    if is_admin():
        conn.execute('''
            INSERT OR REPLACE INTO build_status (build_id, needs_approval, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (build_id, 1))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('build_chat', build_id=build_id))

@app.route('/chat/build/<int:build_id>/approve', methods=['POST'])
def approve_build_changes(build_id):
    """Согласование изменений в сборке"""
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Обновляем статус сборки
    conn.execute('''
        INSERT OR REPLACE INTO build_status (build_id, needs_approval, last_updated)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (build_id, 0))
    
    # Добавляем системное сообщение о согласовании
    conn.execute('''
        INSERT INTO build_chat (build_id, user_id, message, is_admin)
        VALUES (?, ?, ?, ?)
    ''', (build_id, session['user_id'], '✅ Изменения согласованы', 1))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('build_chat', build_id=build_id))

@app.route('/chat/build/<int:build_id>/request_edit', methods=['POST'])
def request_build_edit(build_id):
    """Запрос на редактирование сборки от пользователя"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Проверяем, что сборка принадлежит пользователю
    build = conn.execute('SELECT * FROM user_gadjets WHERE id = ? AND user_id = ?', 
                        (build_id, session['user_id'])).fetchone()
    
    if not build:
        conn.close()
        return redirect(url_for('index'))
    
    # Получаем сообщение из формы
    message = request.form.get('edit_request', '').strip()
    if not message:
        message = "Запрос на редактирование сборки"
    
    # Отправляем запрос на редактирование
    conn.execute('''
        INSERT INTO build_chat (build_id, user_id, message, is_admin)
        VALUES (?, ?, ?, ?)
    ''', (build_id, session['user_id'], f"✏️ ЗАПРОС НА РЕДАКТИРОВАНИЕ: {message}", 0))
    
    # Устанавливаем статус "нужно согласование"
    conn.execute('''
        INSERT OR REPLACE INTO build_status (build_id, needs_approval, last_updated)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (build_id, 1))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('build_chat', build_id=build_id))

@app.route('/api/check_compatibility')
def api_check_compatibility():
    """API для проверки совместимости процессора и материнской платы"""
    cpu = request.args.get('cpu', '')
    mb = request.args.get('mb', '')
    
    if not cpu or not mb:
        return jsonify({'compatible': True, 'message': 'Выберите процессор и материнскую плату'})
    
    is_compatible, message = check_socket_compatibility_simple(cpu, mb)
    
    return jsonify({
        'compatible': is_compatible,
        'message': message
    })

@app.route('/api/check_memory_compatibility')
def check_memory_compatibility(motherboard_name, ram_name):
    """Проверка совместимости оперативной памяти"""
    conn = get_db_connection()
    
    # Получаем информацию о материнской плате
    mb = conn.execute(
        'SELECT memory_type, memory_speed FROM components WHERE name = ? AND category = "Материнская плата"',
        (motherboard_name,)
    ).fetchone()
    
    # Получаем информацию об оперативной памяти
    ram = conn.execute(
        'SELECT memory_type, memory_speed FROM components WHERE name = ? AND category = "Оперативная память"',
        (ram_name,)
    ).fetchone()
    
    conn.close()
    
    if not mb:
        return True, "Материнская плата не найдена"
    
    if not ram:
        return True, "Оперативная память не найдена"
    
    mb_memory_type = mb['memory_type'] or ''
    ram_memory_type = ram['memory_type'] or ''
    mb_memory_speed = mb['memory_speed'] or 0
    ram_memory_speed = ram['memory_speed'] or 0
    
    if not mb_memory_type or not ram_memory_type:
        return True, "⚠️ Тип памяти не указан"
    
    # Проверяем тип памяти
    if mb_memory_type != ram_memory_type:
        return False, f"❌ НЕСОВМЕСТИМО! Материнская плата поддерживает {mb_memory_type}, а память - {ram_memory_type}"
    
    # Проверяем скорость (память может быть быстрее, чем поддерживает мат. плата)
    if ram_memory_speed > mb_memory_speed:
        return True, f"⚠️ Память {ram_memory_speed}МГц будет работать на {mb_memory_speed}МГц (макс. для платы)"
    
    return True, f"✓ Совместимо: {ram_memory_type} {ram_memory_speed}МГц"

@app.route('/admin/components/delete_all', methods=['POST'])
def delete_all_components():
    """Удаление всех комплектующих (только для админа)"""
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    try:
        # Удаляем все комплектующие
        count = conn.execute('SELECT COUNT(*) FROM components').fetchone()[0]
        conn.execute('DELETE FROM components')
        conn.commit()
        
        flash(f'Удалено {count} комплектующих', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('manage_components_page'))

def calculate_build_power_consumption(build):
    """Расчет общего потребления мощности сборки"""
    conn = get_db_connection()
    
    total_power = 0
    components_to_check = [
        ('Процессор', build['Proc']),
        ('Материнская плата', build['MPlata']),
        ('Система охлаждения', build['CW']),
        ('Оперативная память', build['RAM']),
        ('Видеокарта', build['VideoCard']),
        ('Блок питания', build['BP']),
        ('Корпус', build['Corpus'])
    ]
    
    for category, name in components_to_check:
        result = conn.execute(
            '''SELECT COALESCE(power_consumption, tdp, 0) as power 
               FROM components WHERE category = ? AND name = ?''',
            (category, name)
        ).fetchone()
        
        if result:
            power_value = result['power']
            if power_value:
                try:
                    total_power += int(power_value)
                except (ValueError, TypeError):
                    total_power += 0
    
    conn.close()
    return total_power

def calculate_required_psu_wattage(build):
    """Расчет необходимой мощности блока питания"""
    conn = get_db_connection()
    
    # Базовое потребление основных компонентов
    total_power = 0
    
    components = [
        ('Процессор', build['Proc']),
        ('Видеокарта', build['VideoCard']),
        ('Материнская плата', build['MPlata']),
        ('Оперативная память', build['RAM'])
    ]
    
    for category, name in components:
        result = conn.execute(
            '''SELECT COALESCE(power_consumption, tdp, 0) as power 
               FROM components WHERE category = ? AND name = ?''',
            (category, name)
        ).fetchone()
        
        if result and result['power']:
            try:
                total_power += int(result['power'])
            except (ValueError, TypeError):
                pass
    
    conn.close()
    
    # Добавляем запас 30% для стабильности
    recommended_power = int(total_power * 1.3)
    
    # Минимальные значения для разных конфигураций
    if recommended_power < 500:
        recommended_power = 500  # Минимум для современного ПК
    elif recommended_power > 1200:
        recommended_power = 1200  # Максимум для большинства сборок
    
    return recommended_power

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5125)