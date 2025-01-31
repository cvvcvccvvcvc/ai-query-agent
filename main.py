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

load_dotenv()

folder_id = os.getenv('FOLDER_ID')
yandexgpt_key = os.getenv('YANDEXGPT_KEY')
yandex_search_key = os.getenv('YANDEX_SEARCH_KEY')

app = FastAPI()

yandex_gpt_api_url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

class QueryRequest(BaseModel):
    id: int
    query: str

async def yandex_search(query):
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
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    text = await response.text()  # Асинхронно получаем текст ответа
                    root = ET.fromstring(text)
                    results = []
                    
                    for doc in root.findall(".//doc"):
                        url = doc.find("url").text if doc.find("url") is not None else "Нет ссылки"
                        title = doc.find("headline").text if doc.find("headline") is not None else "Нет описания"
                        results.append((title, url))
                    
                    return results
                else:
                    return f"Ошибка: {response.status}"
    except Exception as e:
        return f"Ошибка запроса: {str(e)}"

async def yandex_gpt(query: str):
    messages = [
        {
            "role": "user",
            "text": query
        }
    ]
    
    try:
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
                
                if response.status != 200:
                    return {"error": "Ошибка при запросе к Yandex GPT"}
                
                # Асинхронно получаем ответ и преобразуем его в JSON
                result = await response.json()
                return result
                
    except Exception as e:
        return {"error": f"Ошибка запроса: {str(e)}"}

# Функция для извлечения текста с страницы
def extract_main_text(url):
    # Отправляем запрос к странице
    response = requests.get(url)

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
    return "Основной контент не найден"

@app.post("/api/request")
async def handle_request(request: QueryRequest):
    try:
        sources = [] # хорошие источники 
        main_texts = [] # текст с хороших источников
        checked_sites = []  # ссылки, которые уже были проанализированы
        counter = 0 # счетчик для ограничения источников до 3
        big_question = request.query # сохраним в отдельной переменной весь запрос
        try: # попробуем разделить вопрос и ответ
            question, answers = re.findall(r"([^\n]+)\n(1\..+?4\..+?)(?=\n|$)", big_question, re.DOTALL)[0]
        except: # если не получилось, считаем что ответов нет
            question, answers = big_question, 'В данном вопросе нет вариантов ответа'

        # ищем в поисковике весь запрос и вопрос из запроса для большей вероятности поймать хорошие источники
        urls1 = await yandex_search(big_question)
        urls1 = urls1[:2]
        urls2 = await yandex_search(question)
        urls2 = urls2[:2]
        urls1.extend(urls2)
        
        # итерируемся по источникам
        for _, source_url in urls1:
            if counter == 3 or source_url in checked_sites: # проверяем был ли уже этот источник проанализирован и сколько сейчас хороших источников
                break
            main_text = extract_main_text(source_url)[:500] # извлекаем ключевой текст с ссайта
            
            # узнаем у модели полезна ли ей информация с этого источника
            query = f''' 
            Есть вопрос: {question}. Полезна ли следующая информация для ответа на поставленный вопрос вопрос? В ответ напиши "Да, полезна", если информация полезна и "Нет", если не полезна.
            Информация: {main_text}
            '''
            yandex_gpt_response = await yandex_gpt(query)
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
            ans = None
        else: # в ином случае узнаем ответ у гпт
            query = f'''
            Есть вопрос: {question}. Есть ответы: {answers}. Ответь на вопрос, выбрав один из вариантов: от "1", "2", до "10". Ни больше ни меньше\n
            В качестве ответа верни ровно 1 число из набора, ни словом больше.\n
            Дополнительная информация: {str(main_texts)}\n
            Ответь на вопрос, не добавляя ссылки. Мне нужно только текстовое объяснение, без перенаправлений на другие сайты.'''
            yandex_gpt_response = await yandex_gpt(query)
            ans = yandex_gpt_response['result']['alternatives'][0]['message']['text']
        
        # отдельно просим у гпт пояснения к ответу
        query = f'''
        Есть вопрос: {question}. Есть ответы: {answers}. Ответь на вопрос, выбрав один из вариантов: от "1", "2", до "10"\n
        В качестве ответа верни цифру и Твое объяснение выбора, предпочтительно с цитатой из дополнительной информации (максимум 50 слов) \n
        Дополнительная информация: {str(main_texts)}\n 
        Ответь на вопрос, не добавляя ссылки. Мне нужно только текстовое объяснение, без перенаправлений на другие сайты.
        '''
        yandex_gpt_response = await yandex_gpt(query)
        reason = yandex_gpt_response['result']['alternatives'][0]['message']['text']

       # возвращаем результат
        return JSONResponse(
            content={
                "id": request.id,
                "answer": ans,
                "reasoning": reason,
                "sources": sources
            }
        )

    except KeyError:
        raise HTTPException(status_code=500, detail="Error parsing Yandex GPT response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")





# uvicorn main:app --host 127.0.0.1 --port 8000 --reload
# Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/request" -Method POST -Headers @{ "Content-Type" = "application/json; charset=utf-8" } -Body '{"id": 1, "query": "Привет! Как тебя зовут?"}'
