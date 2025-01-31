FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "./start.sh"]
#RUN chmod +x ./start.sh

#CMD ["./start.sh"]

# docker-compose up --build
# docker-compose up -d
# docker-compose stop
# docker-compose down
# sudo docker logs fastapi-baseline