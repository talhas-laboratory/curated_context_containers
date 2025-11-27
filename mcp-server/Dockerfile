FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir .
EXPOSE 7801
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7801"]
