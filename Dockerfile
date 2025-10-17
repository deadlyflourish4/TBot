# ---- Base image with pyodbc + ODBC driver ----
FROM laudio/pyodbc:3.0.1

# ---- Set working directory ----
WORKDIR /app

# ---- Copy dependency file ----
COPY requirements.txt .

# ---- Install Python dependencies ----
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy source code ----
COPY . .

# ---- Expose port ----
EXPOSE 8000

# ---- Run Uvicorn ----
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
