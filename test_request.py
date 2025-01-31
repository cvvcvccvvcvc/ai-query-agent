import requests
import json
# В каком году Университет ИТМО был включён в число Национальных исследовательских университетов России?\n1. 2007\n2. 2009\n3. 2011\n4. 2015
# 2
# В каком рейтинге (по состоянию на 2021 год) ИТМО впервые вошёл в топ-400 мировых университетов?\n1. ARWU (Shanghai Ranking)\n2. Times Higher Education (THE) World University Rankings\n3. QS World University Rankings\n4. U.S. News & World Report Best Global Universities'
# 3
# В каком городе находится главный кампус Университета ИТМО?\n1. Москва\n2. Санкт-Петербург\n3. Екатеринбург\n4. Нижний Новгород
# 2

que = 'В каком городе находится главный кампус Университета ИТМО?\n1. Москва\n2. Санкт-Петербург\n3. Екатеринбург\n4. Нижний Новгород'

url = "http://localhost:8080/api/request"  # Используем localhost или 127.0.0.1
headers = {"Content-Type": "application/json; charset=utf-8"}
data = {
    "id": 1,
    "query": que
}

response = requests.post(url, headers=headers, data=json.dumps(data))

print("Status code:", response.status_code)
print("Response:", response.json())
