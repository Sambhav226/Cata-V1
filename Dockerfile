FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY coder/ coder/
COPY data/ data/
COPY tests/fixtures/ tests/fixtures/
ENTRYPOINT ["python", "-m", "coder.cli"]
