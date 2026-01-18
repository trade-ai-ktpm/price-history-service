FROM python:3.10-slim

# 1. Set working directory
WORKDIR /app

# 2. Copy & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy source code
COPY app ./app

# 4. Expose port
EXPOSE 8003

# 5. Run app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8003}"]