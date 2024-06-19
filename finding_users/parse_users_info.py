import os
import vk_api
from vk_api import VkApi
from dotenv import load_dotenv
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

your_access_token = os.getenv("USER_TOKEN")
vk_session = VkApi(token=your_access_token)


def search_vk_users(search_parameters):
    """
    Поиск пользователей VK по параметрам
    """
    vk = vk_session.get_api()

    city = search_parameters.get("city", "")
    gender = search_parameters.get("gender", "")
    age = search_parameters.get("age", "")

    gender_map = {"female": 1, "male": 2}
    gender_value = gender_map.get(gender.lower(), 0)

    search_query = {
        "hometown": city,
        "sex": gender_value,
        "age_from": age,
        "age_to": age,
        "count": 10,
        "fields": "city, sex, bdate, photo_max"
    }
    logging.info(f"Запуск поиска пользователей с параметрами: {search_query}")

    try:
        response = vk.users.search(**search_query)
        users = response["items"]
        logging.info(f"Найдено {len(users)} пользователей")

        filtered_users = [user for user in users if user.get("sex") in [1, 2]]

        # Для каждого пользователя получаем топ 3 фотографии
        for user in filtered_users:
            user_id = user["id"]
            try:
                photos = vk.photos.get(owner_id=user_id, album_id="profile", extended=1, count=10)
                photos_items = photos["items"]

                # Выбираем фотографии с максимальным размером
                max_size_photos = []
                for photo in photos_items:
                    max_size_photo = max(photo["sizes"], key=lambda size: size["width"] * size["height"])
                    max_size_photos.append({
                        "url": max_size_photo["url"],
                        "likes": photo["likes"]["count"]
                    })

                # Сортируем фотографии по количеству лайков и выбираем топ 3
                top_photos = sorted(max_size_photos, key=lambda x: x["likes"], reverse=True)[:3]
                user["top_photos"] = [photo["url"] for photo in top_photos]

                time.sleep(0.01)

            except vk_api.exceptions.ApiError as photo_error:
                user["top_photos"] = []
                logging.error(f"Ошибка при получении фотографий пользователя {user_id}: {photo_error}")

        return filtered_users

    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка в работе VK API: {e}")
        return []

