FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# ParsPack معمولاً /data را writable نمی‌دهد؛ /tmp قابل نوشتن است
ENV DB_PATH=/tmp/db.sqlite3

EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
