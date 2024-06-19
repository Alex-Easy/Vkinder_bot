import os
from io import BytesIO
import psycopg2
import re
import requests
from vk_api.upload import VkUpload
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dotenv import load_dotenv
from finding_users.parse_users_info import search_vk_users
from vkinder_db.vkinder_db import insert_data_found_users, insert_data_favorites, select_favorites, clear_favorites
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
vk_token = os.getenv("TOKEN_VK")

authorize = vk_api.VkApi(token=vk_token)
longpoll = VkLongPoll(authorize)
search_parameters = {"city": "", "gender": "", "age": ""}  # параметры, которые передадим в функцию поиска

connection = psycopg2.connect(
    host=os.getenv("HOST"),
    user=os.getenv("LOGIN"),
    password=os.getenv("PASSWORD"),
    database=os.getenv("NAME_DB")
)
connection.autocommit = True


class ButtonVK:
    start = "Начать подбор"
    finish = "Завершить"
    lets_go = "Привет! Я - бот VKinder, который поможет тебе подобрать пару."
    enter_city = "Введите город для поиска:"
    right_city = "Да, верно"
    modify_city = "Изменить город"
    boy = "Парень"
    girl = "Девушка"
    all_true = "Все верно"
    change_parameters = "Изменить параметры"
    city = "Город"
    age = "Возраст"
    gender = "Пол"
    next = "Следующий"
    add_favourites = "Добавить в избранное"
    all_fovourites = "Избранное"
    display = "Начать показ"
    clear_favourites = "Очистить избранное"


def write_message(sender, message, keyboard=None, attachments=None):
    logging.info(f'Отправка сообщения пользователю: {sender}')
    param = {
        "user_id": sender,
        "message": message,
        "random_id": get_random_id(),
    }
    if keyboard is not None:
        param["keyboard"] = keyboard.get_keyboard()
    if attachments is not None:
        param["attachment"] = attachments

    authorize.method("messages.send", param)


def start(user_id):
    logging.info(f'Начали общение с пользователем: {user_id}')
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.start, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)

    # Загружаем и отправляем приветственную картинку
    photo_path = "vkinder_pics/VKinder_banner.png"
    upload = VkUpload(authorize)
    photo_id = upload_photo(upload, photo_path)

    write_message(user_id, "Привет! Я - бот VKinder, который поможет тебе подобрать пару.", keyboard, photo_id)


def finish(user_id):
    logging.info(f'Закончили общение с пользователем: {user_id}')
    write_message(user_id, "До новых встреч!")


def city(user_id):
    logging.info(f'Запросили город для пользователя: {user_id}')
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)
    write_message(user_id, "Введите город для поиска:", keyboard)


def city_confirm(user_id, city):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.right_city, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.modify_city, VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)
    write_message(user_id, f"Начать поиск в городе {city.capitalize()}?", keyboard)


def validate_city_name(city_name):
    """
    Проверяем название города. Название может содержать только буквы, пробелы и тире.
    """
    pattern = re.compile(r"^[a-zA-Zа-яА-ЯёЁ\s-]+$")
    return bool(pattern.match(city_name))


def gender(user_id):
    logging.info(f'Запросили пол для пользователя: {user_id}')
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.boy, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.girl, VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)
    write_message(user_id, "Кто вам нужен?", keyboard)


def age(user_id):
    logging.info(f'Запросили возраст для пользователя: {user_id}')
    write_message(user_id, "укажите возраст")


def get_year_word(age):
    if 11 <= age % 100 <= 19:
        return "лет"
    last_digit = age % 10
    if last_digit == 1:
        return "год"
    elif 2 <= last_digit <= 4:
        return "года"
    else:
        return "лет"


def data_confirm(user_id, gender, city, age):
    logging.info(f'Получили данные для пользователя: {user_id}: {gender}, {city}, {age}')
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.all_true, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.change_parameters, VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)
    get_year_word(age)
    year_word = get_year_word(age)
    write_message(user_id, f"Требуется {gender} из города {city.capitalize()} возраст {age}" + " " + year_word + "?",
                  keyboard)


def data_modify(user_id):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.city, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.age, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.gender, VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)
    write_message(user_id, "Что изменить?", keyboard)


def navigation(user_id):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.next, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.add_favourites, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.all_fovourites, VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)
    write_message(user_id, "-----------------готово----------------", keyboard)


def navigation_for_added_user_and_favourites(user_id):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.next, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.all_fovourites, VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)


def display_user(user_id, user):
    logging.info(f'Показываем пользователя: {user["id"]} пользователю {user_id}')

    vk_id = user["id"]
    first_name = user.get("first_name", "Неизвестно")
    last_name = user.get("last_name", "Неизвестно")
    profile_url = f"https://vk.com/id{vk_id}"
    top_photos = user.get("top_photos", [])

    message = f"{first_name} {last_name}\nПрофиль: {profile_url}\n"

    if top_photos:
        # Загрузка фотографий и получение вложений
        photo_attachments = upload_photos(user_id, top_photos)
        attachment_strings = [
            f"photo{photo['owner_id']}_{photo['id']}" for photo in photo_attachments
        ]
        write_message(user_id, message, attachments=",".join(attachment_strings))
    else:
        message += "Нет доступных фотографий."
        write_message(user_id, message)
    navigation(user_id)


def display_favorites(user_id, favorites):
    if favorites:
        for user in favorites:
            display_user(user_id, user)
        navigation_for_favorites(user_id)
    else:
        write_message(user_id, "Избранных пользователей нет.")
        navigation(user_id)


def navigation_for_favorites(user_id):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(ButtonVK.next, VkKeyboardColor.PRIMARY)
    keyboard.add_button(ButtonVK.clear_favourites, VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button(ButtonVK.finish, VkKeyboardColor.NEGATIVE)
    write_message(user_id, "--------------конец списка-------------", keyboard)


def main():
    logging.info("Бот запущен")
    search_parameters = {"city": "", "gender": "", "age": ""}
    flag = ""
    search_results = []
    current_index = 0

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            msg = event.text
            user_id = event.user_id

            if msg == "Начать":
                start(user_id)

            elif msg == ButtonVK.finish:
                finish(user_id)

            elif msg == ButtonVK.start:
                city(user_id)
                flag = "city"

            elif flag == "city":
                city_confirm(user_id, msg)
                flag = msg

            elif msg == ButtonVK.right_city and flag != "data confirm":
                city_search = flag
                search_parameters["city"] = city_search.capitalize()
                flag = "gender"
                gender(user_id)

            elif msg == ButtonVK.modify_city:
                city(user_id)
                if search_parameters["gender"] == "":
                    flag = "city"
                else:
                    flag = "modify city"

            elif msg == ButtonVK.boy and flag != "modify gender":
                gender_search = msg
                search_parameters["gender"] = "male"
                age(user_id)
                flag = "age"

            elif msg == ButtonVK.girl and flag != "modify gender":
                gender_search = msg
                search_parameters["gender"] = "female"
                age(user_id)
                flag = "age"

            elif msg == ButtonVK.boy and flag == "modify gender":
                gender_search = msg
                search_parameters["gender"] = "male"
                flag = "data confirm"
                data_confirm(user_id, gender_search, city_search, age_search)

            elif msg == ButtonVK.girl and flag == "modify gender":
                gender_search = msg
                search_parameters["gender"] = "female"
                flag = "data confirm"
                data_confirm(user_id, gender_search, city_search, age_search)

            elif flag == "age":
                try:
                    age_search = int(msg)
                    search_parameters["age"] = age_search
                    flag = "data confirm"
                    data_confirm(user_id, gender_search, city_search, age_search)
                except ValueError:
                    write_message(user_id, "Пожалуйста, введите корректный возраст")

            elif msg == ButtonVK.all_true and flag == "data confirm":
                write_message(user_id, "Ищу подходящие анкеты...")
                search_results = search_vk_users(search_parameters)
                if search_results:
                    display_user(user_id, search_results[0])
                    flag = "navigation"
                else:
                    write_message(user_id, "Не найдено пользователей по данным параметрам.")
                    start(user_id)

            elif msg == ButtonVK.change_parameters and flag == "data confirm":
                data_modify(user_id)

            elif msg == ButtonVK.city:
                city(user_id)
                flag = "modify city"

            elif msg == ButtonVK.age:
                age(user_id)
                flag = "age"

            elif msg == ButtonVK.gender:
                gender(user_id)
                flag = "modify gender"

            elif msg == ButtonVK.next and flag == "navigation":
                current_index = (current_index + 1) % len(search_results)
                display_user(user_id, search_results[current_index])

            elif msg == ButtonVK.add_favourites and flag == "navigation":
                user_id_db = insert_data_found_users(
                    vk_id=search_results[current_index]["id"],
                    first_name=search_results[current_index].get("first_name", "Неизвестно"),
                    last_name=search_results[current_index].get("last_name", "Неизвестно"),
                    city=search_parameters["city"],
                    gender=search_parameters["gender"],
                    age=search_parameters["age"],
                    top_photos=search_results[current_index].get("top_photos", [])
                )
                insert_data_favorites(user_id_db)
                write_message(user_id, "Пользователь добавлен в избранное")
                navigation(user_id)

            elif msg == ButtonVK.all_fovourites:
                favorites = select_favorites()
                display_favorites(user_id, favorites)

            elif msg == ButtonVK.clear_favourites:
                clear_favorites()
                write_message(user_id, "Избранное очищено.")
                navigation(user_id)

def upload_photo(upload, photo_path):
    try:
        photo = upload.photo_messages(photo_path)[0]
        return f"photo{photo['owner_id']}_{photo['id']}"
    except Exception as e:
        logging.error(f"Ошибка при загрузке изображения: {e}")
        return None

def upload_photos(user_id, photo_urls):
    """
    Загрузка фотографий на сервер VK и получение attachment.
    """
    upload = VkUpload(authorize)
    photo_attachments = []

    for url in photo_urls:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                photo_data = BytesIO(response.content)
                # Загружаем фото на сервер VK
                photo = upload.photo_messages(photos=photo_data)[0]
                # Формируем аттачмент
                photo_attachments.append({
                    "owner_id": photo['owner_id'],
                    "id": photo['id']
                })
            else:
                logging.warning(f"Не удалось загрузить фотографию по URL: {url}")
        except Exception as e:
            logging.error(f"Ошибка при загрузке или отправке фотографии: {e}")

    return photo_attachments


if __name__ == "__main__":
    main()
