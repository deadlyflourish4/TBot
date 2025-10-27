# ---- Base image with pyodbc + ODBC driver ----
FROM laudio/pyodbc:3.0.0

# ---- Set working directory ----
WORKDIR /app

# ---- Copy dependency file ----
COPY requirements.txt .

# ---- Install Python dependencies ----
RUN pip install --upgrade pip setuptools wheel    
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy source code ----
COPY . .

# ---- Expose port ----
EXPOSE 8080

# ---- Run Uvicorn ----
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
