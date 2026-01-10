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
    
    # Таблица с комплектующими
    c.execute('''
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            price REAL DEFAULT 0,
            socket TEXT
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
            ('Процессор', 'Intel Core i5-12400F', '6 ядер, 2.5-4.4 ГГц', 15000),
            ('Процессор', 'AMD Ryzen 5 5600X', '6 ядер, 3.7-4.6 ГГц', 14000),
            ('Процессор', 'Intel Core i7-12700K', '12 ядер, 3.6-5.0 ГГц', 25000),
            ('Материнская плата', 'ASUS PRIME B660M-A', 'LGA 1700, DDR4', 8000),
            ('Материнская плата', 'GIGABYTE B550 AORUS ELITE', 'AM4, DDR4', 9000),
            ('Материнская плата', 'MSI MAG Z690 TOMAHAWK', 'LGA 1700, DDR5', 15000),
            ('Система охлаждения', 'DeepCool AK620', 'Башенный, 2x120мм', 4000),
            ('Система охлаждения', 'Noctua NH-D15', 'Башенный, 2x140мм', 8000),
            ('Система охлаждения', 'ID-COOLING SE-224-XT', 'Башенный, 120мм', 2000),
            ('Оперативная память', 'Kingston FURY Beast 16GB', 'DDR4 3200МГц', 4000),
            ('Оперативная память', 'Corsair Vengeance RGB 32GB', 'DDR4 3600МГц', 8000),
            ('Оперативная память', 'G.Skill Trident Z5 32GB', 'DDR5 6000МГц', 12000),
            ('Видеокарта', 'NVIDIA GeForce RTX 3060', '12GB GDDR6', 30000),
            ('Видеокарта', 'AMD Radeon RX 6700 XT', '12GB GDDR6', 35000),
            ('Видеокарта', 'NVIDIA GeForce RTX 4090', '24GB GDDR6X', 150000),
            ('Блок питания', 'Be quiet! System Power 9 600W', '600W, 80+ Bronze', 5000),
            ('Блок питания', 'Corsair RM750x 750W', '750W, 80+ Gold', 9000),
            ('Блок питания', 'Seasonic PRIME TX-1000', '1000W, 80+ Titanium', 20000),
            ('Корпус', 'DeepCool MATREXX 55', 'ATX, стеклянная боковая', 4000),
            ('Корпус', 'NZXT H510 Flow', 'ATX, меш-фасад', 7000),
            ('Корпус', 'Lian Li O11 Dynamic', 'E-ATX, двойная камера', 12000),
        ]
        
        for component in test_components:
            try:
                c.execute('''
                    INSERT INTO components (category, name, description, price)
                    VALUES (?, ?, ?, ?)
                ''', component)
            except sqlite3.IntegrityError:
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
    
    # Если не нашли процессор
    if not cpu:
        return False, "Процессор не найден в базе данных"
    
    # Если не нашли материнскую плату
    if not mb:
        return False, "Материнская плата не найдена в базе данных"
    
    cpu_socket = cpu['socket'] or ''
    mb_socket = mb['socket'] or ''
    
    # Если у процессора нет сокета в базе
    if not cpu_socket:
        return True, "⚠️ Сокет процессора не указан в базе. Проверка невозможна."
    
    # Если у материнской платы нет сокета в базе
    if not mb_socket:
        return True, "⚠️ Сокет материнской платы не указан в базе. Проверка невозможна."
    
    # Нормализуем сокеты
    cpu_socket = cpu_socket.upper().strip()
    mb_socket = mb_socket.upper().strip()
    
    # Проверяем совместимость
    if cpu_socket == mb_socket:
        return True, f"✓ Отлично! Сокеты совпадают: {cpu_socket}"
    
    # Проверяем совместимость Intel
    if 'LGA' in cpu_socket and 'LGA' in mb_socket:
        # Разные LGA сокеты несовместимы
        return False, f"❌ НЕСОВМЕСТИМО! Процессор ({cpu_socket}) не подходит к материнской плате ({mb_socket})"
    
    # Проверяем совместимость AMD
    if 'AM' in cpu_socket and 'AM' in mb_socket:
        if cpu_socket == mb_socket:
            return True, f"✓ Отлично! Сокеты совпадают: {cpu_socket}"
        else:
            return False, f"❌ НЕСОВМЕСТИМО! {cpu_socket} не совместим с {mb_socket}"
    
    # Смешанные платформы (Intel + AMD)
    if ('LGA' in cpu_socket and 'AM' in mb_socket) or ('AM' in cpu_socket and 'LGA' in mb_socket):
        return False, f"❌ НЕСОВМЕСТИМО! Intel и AMD платформы несовместимы"
    
    return True, f"ℹ️ Сокеты разные: {cpu_socket} → {mb_socket}. Проверьте документацию."
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
        SELECT category, name, description, price, socket 
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
            'socket': comp['socket']
        })
    
    # Получаем сборки пользователя
    passwords = conn.execute('''
        SELECT * FROM user_gadjets 
        WHERE user_id = ? 
        ORDER BY id DESC
    ''', (session['user_id'],)).fetchall()
    
    # Рассчитываем цены для каждой сборки
    builds_with_prices = []
    total_user_price = 0
    
    for build in passwords:
        build_dict = dict(build)
        build_price = 0
        
        # Рассчитываем цену для каждой сборки
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
                build_price += float(price_result['price'])
        
        build_dict['total_price'] = build_price
        builds_with_prices.append(build_dict)
        total_user_price += build_price
    
    conn.close()
    
    return render_template('index.html', 
                         passwords=builds_with_prices,
                         username=session['username'],
                         is_admin=is_admin(),
                         total_user_price=total_user_price,
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
        # Временно закомментируем проверку совместимости
        # is_compatible, message = check_socket_compatibility_simple(Proc, MPlata)
        
        # # Если несовместимо, показываем ошибку и не сохраняем
        # if not is_compatible:
        #     flash(f'ОШИБКА: {message}', 'error')
        #     return redirect(url_for('index'))
        
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
        ''', (build_id, session['user_id'], 'Сборка создана', 0))
        
        conn.commit()
        conn.close()
        
        # Временно закомментируем flash
        # flash('Сборка успешно создана!', 'success')
    
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
            ('Кулер', build['CW']),
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
            changes.append(f"Кулер: {old_build_dict.get('CW', '')} → {CW}")
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
        SELECT id, name, description, price, socket 
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
            'socket': component['socket']
        })
    
    return jsonify(components_list)

@app.route('/api/components')
def get_all_components():
    """API для получения всех комплектующих"""
    conn = get_db_connection()
    components = conn.execute('''
        SELECT category, name, description, price 
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
        
        try:
            price = float(price_str) if price_str else 0.0
        except ValueError:
            price = 0.0
        
        try:
            conn.execute('''
                INSERT OR REPLACE INTO components (category, name, description, price, socket)
                VALUES (?, ?, ?, ?, ?)
            ''', (category, name, description, price, socket))
            conn.commit()
        except sqlite3.IntegrityError as e:
            print(f"Ошибка добавления компонента: {e}")
        
        # Важно: после POST запроса тоже нужно что-то вернуть!
        # Либо редирект, либо рендер шаблона
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
    
    try:
        price = float(price_str) if price_str else 0.0
    except ValueError:
        price = 0.0
    
    if component_id and category and name:
        conn = get_db_connection()
        conn.execute('''
            UPDATE components 
            SET category = ?, name = ?, description = ?, price = ?
            WHERE id = ?
        ''', (category, name, description, price, component_id))
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5125)