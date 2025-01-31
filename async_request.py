import aiohttp
import asyncio
import json

async def send_request(session, url, que):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = {
        "id": 1,
        "query": que
    }
    async with session.post(url, headers=headers, json=data) as response:
        status = response.status
        response_json = await response.json()
        print("Status code:", status)
        print("Response:", response_json)

async def main():
    url = "http://127.0.0.1:8000/api/request"
    que_list = [
        'В каком году Университет ИТМО был включён в число Национальных исследовательских университетов России?\n1. 2007\n2. 2009\n3. 2011\n4. 2015',
        'В каком городе находится главный кампус Университета ИТМО?\n1. Москва\n2. Санкт-Петербург\n3. Екатеринбург\n4. Нижний Новгород\n5. Сталинград\n6. Ленинград'
    ]
    
    async with aiohttp.ClientSession() as session:
        tasks = [send_request(session, url, que) for que in que_list]
        await asyncio.gather(*tasks)  # Параллельное выполнение запросов

# Запуск асинхронной функции
asyncio.run(main())
