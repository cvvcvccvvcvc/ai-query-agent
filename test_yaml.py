import requests
from dotenv import load_dotenv
import os



load_dotenv()
folder_id = os.getenv('FOLDER_ID')
yandexgpt_key = os.getenv('YANDEXGPT_KEY')
yandex_search_key = os.getenv('YANDEX_SEARCH_KEY')

def yandex_search(query):
    # Это гарантирует, что одновременно не будет больше 2 запросов
    user = 'default'
    url = 'https://yandex.ru/search/xml'
    params = {
        'user': user,
        'apikey': yandex_search_key,
        'l10n': 'ru',
        'query': query,
        'folderid': folder_id,
        'region': 2
    }

    return requests.get(url, params=params).text

print(yandex_search('в каком я городе?'))