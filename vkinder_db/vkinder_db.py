import os
import psycopg2
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

dbname = os.getenv("NAME_DB")
user = os.getenv("LOGIN")
password = os.getenv("PASSWORD")
host = os.getenv("HOST")
port = os.getenv("PORT")
db_name = os.getenv("NAME_DB")

try:
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name,
        port=port
    )
    connection.autocommit = True
    logging.info("Успешное подключение к базе данных")
except Exception as e:
    logging.error(f"Ошибка подключения к базе данных: {e}")
    raise


def create_table_found_users():
    """
    Создаем таблицу для найденных пользователей.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS found_users (
                id SERIAL PRIMARY KEY,
                vk_id VARCHAR(20) NOT NULL UNIQUE,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(25) NOT NULL,
                city VARCHAR(100),
                gender VARCHAR(10),
                age INTEGER,
                top_photos TEXT[]
            );"""
        )
    logging.info("Таблица найденных пользователей была создана.")


def create_table_favorites():
    """
    Создаем таблицу для избранных пользователей.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES found_users(id) ON DELETE CASCADE
            );"""
        )
    logging.info("Таблица избранных пользователей была создана.")


def select_favorites():
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM favorites LIMIT 1")
        columns = [desc[0] for desc in cursor.description]
        logging.info("Columns in the 'favorites' table: %s", columns)

        cursor.execute("""
            SELECT fu.id, fu.first_name, fu.last_name, fu.city, fu.gender, fu.age, fu.top_photos
            FROM favorites f
            JOIN found_users fu ON f.user_id = fu.id
        """)
        rows = cursor.fetchall()
        favorites = []
        for row in rows:
            user = {
                "id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "city": row[3],
                "gender": row[4],
                "age": row[5],
                "top_photos": row[6]
            }
            favorites.append(user)
    return favorites


def drop_tables():
    """
    Удаление таблиц.
    """
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS favorites CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS found_users CASCADE;")
    logging.info('Таблицы успешно удалены.')


def creating_database():
    create_table_found_users()
    create_table_favorites()


# Создание таблиц при запуске
creating_database()


def insert_data_found_users(vk_id, first_name, last_name, city, gender, age, top_photos):
    """
    Вставка данных в таблицу found_users.
    """
    with connection.cursor() as cursor:
        try:
            # Проверка на существование пользователя
            cursor.execute("SELECT id FROM found_users WHERE vk_id = %s", (str(vk_id),))
            user_id = cursor.fetchone()
            if user_id:
                return user_id[0]
            else:
                # Вставка нового пользователя
                cursor.execute(
                    """
                    INSERT INTO found_users (vk_id, first_name, last_name, city, gender, age, top_photos)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (str(vk_id), first_name, last_name, city, gender, age, top_photos)
                )
                user_id = cursor.fetchone()
                if user_id:
                    return user_id[0]
                else:
                    logging.error("Не удалось получить user_id после вставки")
                    return None
        except Exception as e:
            logging.error(f"Ошибка при вставке данных: {e}")
            return None


def insert_data_favorites(user_id):
    """
    Вставка данных в таблицу favorites.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO favorites (user_id)
               VALUES (%s)
               ON CONFLICT DO NOTHING;""",
            (user_id,)
        )
        logging.info(f"Добавлен в избранное пользователь с ID {user_id}")


def select_found_users():
    """
    Выборка всех пользователей из found_users.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM found_users;")
        users = cursor.fetchall()
        logging.info(f"Выбраны все найденные пользователи, всего {len(users)}")
        return users


def get_next_user(found_users, current_index):
    """
    Получение следующего пользователя.
    """
    if found_users:
        next_index = (current_index + 1) % len(found_users)
        next_user = found_users[next_index]
        logging.info(f"Следующий пользователь с индексом {next_index}")
        return next_user, next_index
    logging.info("Список пользователей пуст")
    return None, current_index


def clear_favorites():
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM favorites")
    except Exception as e:
        logging.error(f"Ошибка при очистке избранного: {e}")
