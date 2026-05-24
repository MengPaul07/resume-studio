FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/
COPY frontend/dist/ ./frontend/dist/

EXPOSE 8000

CMD ["python", "-m", "src.main"]
