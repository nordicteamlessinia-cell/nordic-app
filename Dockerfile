FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api_nordic.py .
COPY start_api.sh .

RUN chmod +x /app/start_api.sh

CMD ["/app/start_api.sh"]
