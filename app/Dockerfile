FROM python:3.11-slim

# ===============================
# Environment
# ===============================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ===============================
# System dependencies
# (cần cho pyodbc, sentence-transformers, torch)
# ===============================
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# Python dependencies
# ===============================
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ===============================
# App source
# ===============================
COPY . .

EXPOSE 8000

# ===============================
# Run FastAPI
# ===============================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
