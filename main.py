from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import re
from dotenv import load_dotenv
import os
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import logging
from itertools import chain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()
folder_id = os.getenv('FOLDER_ID')
yandexgpt_key = os.getenv('YANDEXGPT_KEY')
yandex_search_key = os.getenv('YANDEX_SEARCH_KEY')

app = FastAPI()

yandex_gpt_api_url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

class QueryRequest(BaseModel):
    """
    Модель запроса для передачи ID и строки запроса.

    Attributes:
        id (int): Уникальный идентификатор запроса.
        query (str): Строка вопроса с ответами или бесь.
    """
    id: int
    query: str

def yandex_search(query: str):
    """
    Выполняет поиск по запросу на Яндексе с использованием API Яндекса.

    Аргументы:
        query (str): Строка поискового запроса.

    Возвращает:
        list или str: Если запрос успешен, возвращает список из кортежей с заголовками и URL-адресами.
        Если произошла ошибка, возвращает строку с описанием ошибки.
    """
    user = 'default'
    url = 'https://yandex.ru/search/xml'
    params = {
        'user': user,
        'apikey': yandex_search_key,
        'l10n': 'ru',
        'query': query,
        'folderid': folder_id
    }

    try:
        # Выполняем GET-запрос с параметрами
        response = requests.get(url, params=params)
        # Если статус 200, то разбираем ответ
        if response.status_code == 200:
            text = response.text 
            root = ET.fromstring(text)
            results = []
            # Проверяем, если нет найденных документов
            if len(root.findall(".//doc")) == 0:
                logger.info(f'Запрос {query[:20]}, слишком быстро')
             # Извлекаем информацию из каждого документа
            for doc in root.findall(".//doc"):
                url = doc.find("url").text if doc.find("url") is not None else "Нет ссылки"
                title = doc.find("headline").text if doc.find("headline") is not None else "Нет описания"
                results.append((title, url))
            return results
        else:
            return f"Ошибка: {response.status_code}"
    except Exception as e:
        return f"Ошибка запроса: {str(e)}"

async def yandex_gpt(query: str):
    """
    Выполняет асинхронный запрос к API Яндекс GPT с заданным запросом.

    Аргументы:
        query (str): Строка поискового запроса, которую нужно передать в GPT.

    Возвращает:
        dict: Ответ от API, либо сообщение об ошибке в случае неудачи.
    """
    # Сообщения, которые будут отправлены в модель GPT
    messages = [
        {
            "role": "user",
            "text": query
        }
    ]
    
    retries = 100  # Число попыток
    delay = 1  # Задержка между попытками (в секундах)
    
    for attempt in range(retries):
        try:
            # Создаем асинхронную сессию для отправки запроса
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    yandex_gpt_api_url,
                    headers={
                        "Authorization": f"Api-Key {yandexgpt_key}",
                        "x-folder-id": folder_id
                    },
                    json={
                        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
                        "completionOptions": {
                            "stream": False,
                            "temperature": 0.6
                        },
                        "messages": messages
                    }
                ) as response:
                    # Обрабатываем ошибку "слишком много запросов"
                    if response.status == 429:
                        logger.info(f"Слишком много запросов. Попытка {attempt + 1} из {retries}. Ожидание {delay} сек.")
                        await asyncio.sleep(delay)  # Задержка перед повторной попыткой
                        delay += 1  # Увеличиваем задержку в случае очередной ошибки
                        continue
                    # Логируем ошибку при запросе, если статус не 200
                    if response.status != 200:
                        logger.info(f'Запрос {query[:20]}\n{response.status}\n{await response.text()}')
                        return 'Не знаю'
                    result = await response.json()
                    return result
        except Exception as e:
            return {"error": f"Ошибка запроса: {str(e)}"}
    return {"error": "Превышено количество попыток"}

def extract_main_text(url):
    """
    Извлекает основной текст с веб-страницы по заданному URL.

    Функция отправляет GET-запрос по указанному URL, парсит HTML-контент страницы 
    с помощью BeautifulSoup и пытается извлечь текст из различных тегов, таких как:
    <article>, <main>, или <p>.

    Аргументы:
        url (str): URL страницы, с которой нужно извлечь текст.

    Возвращает:
        str: Основной текст страницы или сообщение об ошибке:
            - Если страница не загружается, возвращается "Нет".
            - Если страница не содержит текста в ожидаемых тегах, возвращается "Нет".
            - В случае ошибки при загрузке страницы возвращается сообщение вида: 
              "Ошибка при загрузке страницы: <код ошибки>".
    """
    try:
        response = requests.get(url)
    except:
        return "Нет"
    
    if response.status_code != 200:
        return f"Ошибка при загрузке страницы: {response.status_code}"

    # Парсим HTML-страницу
    soup = BeautifulSoup(response.content, 'html.parser')

    # Попробуем найти текст из различных типов тегов
    # 1. Ищем в <article> (часто используется для основной статьи)
    article = soup.find('article')
    if article:
        return article.get_text(separator=' ', strip=True)

    # 2. Ищем в <main> (некоторые страницы используют это как основной блок контента)
    main = soup.find('main')
    if main:
        return main.get_text(separator=' ', strip=True)

    # 3. Ищем в теге <p> (параграфы могут содержать основную информацию)
    paragraphs = soup.find_all('p')
    if paragraphs:
        return ' '.join([p.get_text(strip=True) for p in paragraphs])

    # 4. Если ничего не нашли, возвращаем ошибку
    return "Нет"

@app.post("/api/request")
async def handle_request(request: QueryRequest):
    """
    Обрабатывает запрос от клиента, выполняет поиск и анализирует источники для ответа на вопрос с помощью Yandex GPT.

    Аргументы:
        request (QueryRequest): Структура данных, содержащая идентификатор запроса и сам текст запроса.

    Возвращает:
        JSONResponse: Ответ в формате JSON с полями:
            - id (int): Идентификатор запроса.
            - answer (str or None): Ответ на вопрос или None, если вариантов ответа нет.
            - reasoning (str): Объяснение выбора ответа, предпочтительно с цитатой из текста источников.
            - sources (list of str): Список источников, которые были использованы для получения информации.
    """
    try: 
        sources = [] # хорошие источники 
        main_texts = [] # текст с хороших источников
        checked_sites = []  # ссылки, которые уже были проанализированы
        counter = 0 # счетчик для ограничения источников до 3
        big_question = request.query # сохраним в отдельной переменной весь запрос
        try: # попробуем разделить вопрос и ответ
            question, answers = re.split(r'(?=\n1)', big_question, maxsplit=1)
            answers = answers.lstrip('\n')
        except: # если не получилось, считаем что ответов нет
            question, answers = big_question, 'В данном вопросе нет вариантов ответа'

        # ищем в поисковике весь запрос и вопрос из запроса для большей вероятности поймать хорошие источники
        urls1 = yandex_search(big_question)
        if urls1:
            urls1 = urls1[:4]

        urls2 = yandex_search(question)
        if urls2:
            urls2 = urls2[:4]
        
        if urls1 and urls2:
            urls = list(chain(*zip(urls1, urls2)))
        elif urls2:   
            urls = urls2
        elif urls1:
            urls = urls1
        else:
            urls = []

        if urls:
            # Полезны ли эти источники? Давайте фильтровать
            for _, source_url in urls:
                # проверяем был ли уже этот источник проанализирован и сколько сейчас хороших источников
                if counter == 3: 
                    break
                if source_url in checked_sites:
                    continue
                main_text = extract_main_text(source_url)[:2000] # извлекаем ключевой текст с ссайта
                if main_text == 'Нет':
                    break
                # узнаем у модели полезна ли ей информация с этого источника
                query = f'''Есть вопрос: {question}. Полезна ли следующая информация для ответа на поставленный вопрос вопрос? В ответ напиши "Да, полезна", если информация полезна и "Нет", если не полезна.
                Информация: {main_text}
                '''
                yandex_gpt_response = await yandex_gpt(query)
                yandex_gpt_response["result"]["alternatives"][0]["message"]["text"]

                answer = yandex_gpt_response['result']['alternatives'][0]['message']['text']
                
                checked_sites.append(source_url)

                # если полезна, сохраняем источник и текст
                if answer == 'Да, полезна':
                    sources.append(source_url)
                    main_texts.append(main_text)
                    counter += 1
                else:
                    pass
        
        # если ответов нет, то возвращаем null в answer поле
        if answers == 'В данном вопросе нет вариантов ответа':
            ans = 'null'
        else: # в ином случае узнаем ответ у гпт
            query = f'''Есть вопрос: {question}. Есть ответы: {answers}. Ответь на вопрос, выбрав один из вариантов: от "1", "2", до "10". Ни больше ни меньше\n
            В качестве ответа верни ровно 1 число из набора, ни словом больше.\n
            Дополнительная информация: {str(main_texts)}\n
            Ответь на вопрос, не добавляя ссылки. Мне нужно только текстовое объяснение, без перенаправлений на другие сайты.'''
            yandex_gpt_response = await yandex_gpt(query)
            ans = yandex_gpt_response['result']['alternatives'][0]['message']['text']
        
        # отдельно просим у гпт пояснения к ответу
        query = f'''Есть вопрос: {question}. Есть ответы: {answers}. Ответь на вопрос, выбрав один из вариантов: от "1", "2", до "10"\n
        В качестве ответа верни цифру и Твое объяснение выбора, предпочтительно с цитатой из дополнительной информации (максимум 50 слов) \n
        Дополнительная информация: {str(main_texts)}\n 
        Ответь на вопрос, не добавляя ссылки. Мне нужно только текстовое объяснение, без перенаправлений на другие сайты.
        '''
        yandex_gpt_response = await yandex_gpt(query)
        reason = yandex_gpt_response['result']['alternatives'][0]['message']['text']
        if reason[0] in '1234567890':
            if reason[0] != ans:
                print(f'here! was {ans}, now {reason[0]}!')
                ans = int(reason[0])
       # Возвращаем ответ в формате JSON
        return JSONResponse(
            content={
                "id": request.id,
                "answer": ans,
                "reasoning": reason + '\nОтвет сгенерирован с помощью YandexGPT',
                "sources": sources
            }
        )

    except KeyError:
        raise HTTPException(status_code=500, detail="Error parsing Yandex GPT response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# uvicorn main:app --host 127.0.0.1 --port 8080 --reload