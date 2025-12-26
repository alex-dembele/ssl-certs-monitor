FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -c "import json, os; os.path.exists('domains.json') or json.dump(['google.com'], open('domains.json', 'w'))"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]