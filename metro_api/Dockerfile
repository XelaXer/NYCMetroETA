FROM python:3.11-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir poetry==1.8.3
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --without-hashes -o requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8000
ENTRYPOINT ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
