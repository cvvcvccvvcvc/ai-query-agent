from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import re
from dotenv import load_dotenv
import os

load_dotenv()

folder_id = os.getenv('FOLDER_ID')
yandexgpt_key = os.getenv('YANDEXGPT_KEY')
yandex_search_key = os.getenv('YANDEX_SEARCH_KEY')

app = FastAPI()

yandex_gpt_api_url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

class QueryRequest(BaseModel):
    id: int
    query: str

import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

def yandex_search(query):
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
        response = requests.get(url, params=params)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            results = []
            
            for doc in root.findall(".//doc"):
                url = doc.find("url").text if doc.find("url") is not None else "Нет ссылки"
                title = doc.find("headline").text if doc.find("headline") is not None else "Нет описания"
                results.append((title, url))
            
            return results
        else:
            return f"Ошибка: {response.status_code}"
    except:
        pass

def yandex_gpt(query: str):
    messages = [
        {
            "role": "user",
            "text": query
        }
    ]
    
    response = requests.post(
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
        },
    )
    
    if response.status_code != 200:
        return {"error": "Ошибка при запросе к Yandex GPT"}
    
    return response.json()


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

# Пример URL
url = "https://news.itmo.ru/ru/university_live/ratings/news/10389/"

@app.post("/api/request")
async def handle_request(request: QueryRequest):
    try:
        sources = []
        main_texts = []
        checked_sites = []
        counter = 0
        big_question = request.query
        question, ans = re.findall(r"([^\n]+)\n(1\..+?4\..+?)(?=\n|$)", big_question, re.DOTALL)[0]

        res1 = yandex_search(big_question)
        res2 = yandex_search(question)
        for _, source_url in res1[:2]:
            if counter == 3 or source_url in checked_sites:
                break
            main_text = extract_main_text(source_url)[:500]
            #print(f'чекаю сайт {source_url}')
            query = f'''
            Есть вопрос: {question}. Полезна ли следующая информация для ответа на поставленный вопрос вопрос? В ответ напиши "Да, полезна", если информация полезна и "Нет", если не полезна.
            Информация: {main_text}
            '''
            answer = yandex_gpt(query)['result']['alternatives'][0]['message']['text']
            checked_sites.append(source_url)
        
            if answer == 'Да, полезна':
                #print('тема')
                sources.append(source_url)
                main_texts.append(main_text)
                counter += 1
            else:
                #print(f'не то: {main_text}')
                pass

        for _, source_url in res2[:2]:
            if counter == 3 or source_url in checked_sites:
                break 
            main_text = extract_main_text(source_url)[:500]
            #print(f'чекаю сайт {source_url}') 
            query = f''' 
            Есть вопрос: {question}. Полезна ли следующая информация для ответа на поставленный вопрос вопрос? В ответ напиши "Да, полезна", если информация полезна и "Нет", если не полезна.
            Информация: {main_text}
            '''
            answer = yandex_gpt(query)['result']['alternatives'][0]['message']['text']
            
            checked_sites.append(source_url)

            if answer == 'Да, полезна':
                #print('тема')
                sources.append(source_url)
                main_texts.append(main_text)
                counter += 1
            else:
                #print(f'не то: {main_text}')
                pass
            if counter == 3:
                break

        query = f'''
        Есть вопрос: {question}. Есть ответы: {ans}. Ответь на вопрос, выбрав один из вариантов: "1", "2", "3" или "4"
        В качестве ответа верни ровно 1 число из набора, ни словом больше.\n
        Дополнительная информация: {str(main_texts)}\n
        Ответь на вопрос, не добавляя ссылки. Мне нужно только текстовое объяснение, без перенаправлений на другие сайты.'''
        ans = yandex_gpt(query)['result']['alternatives'][0]['message']['text']
        
        query = f'''
        Есть вопрос: {question}. Есть ответы: {ans}. Ответь на вопрос, выбрав один из вариантов: "1", "2", "3" или "4"
        В качестве ответа верни цифру и Твое объяснение выбора, предпочтительно с цитатой из дополнительной информации (максимум 50 слов) \n
        Дополнительная информация: {str(main_texts)}\n 
        Ответь на вопрос, не добавляя ссылки. Мне нужно только текстовое объяснение, без перенаправлений на другие сайты.
        '''
        reason = yandex_gpt(query)['result']['alternatives'][0]['message']['text']
        print(main_texts)
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
