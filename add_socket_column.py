import sqlite3

conn = sqlite3.connect('db.db')
cursor = conn.cursor()

# Добавляем колонку socket, если её нет
try:
    cursor.execute("ALTER TABLE components ADD COLUMN socket TEXT")
    print("Колонка socket добавлена")
except sqlite3.OperationalError as e:
    print(f"Колонка уже существует или ошибка: {e}")

# Обновляем существующие записи с информацией о сокетах
socket_updates = [
    # Процессоры
    ('Intel Core i5-12400F', 'LGA1700'),
    ('Intel Core i7-12700K', 'LGA1700'),
    ('Intel Core i3-12100F', 'LGA1700'),
    ('Intel Core i9-13900K', 'LGA1700'),
    ('AMD Ryzen 5 5600X', 'AM4'),
    ('AMD Ryzen 7 7700X', 'AM5'),
    ('AMD Ryzen 9 7950X', 'AM5'),
    
    # Материнские платы
    ('ASUS PRIME B660M-A', 'LGA1700'),
    ('MSI MAG Z690 TOMAHAWK', 'LGA1700'),
    ('ASRock H610M-HDV', 'LGA1700'),
    ('GIGABYTE Z790 AORUS ELITE AX', 'LGA1700'),
    ('GIGABYTE B550 AORUS ELITE', 'AM4'),
    ('ASUS TUF GAMING B650-PLUS', 'AM5'),
    ('MSI B550-A PRO', 'AM4'),
]

for name, socket in socket_updates:
    cursor.execute("UPDATE components SET socket = ? WHERE name = ?", (socket, name))
    print(f"Обновлен {name}: socket = {socket}")

conn.commit()
conn.close()
print("Обновление завершено!")