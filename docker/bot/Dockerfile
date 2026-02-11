FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml* requirements*.txt* /app/

RUN pip install --no-cache-dir --upgrade pip

COPY . /app

CMD ["python", "-m", "app.main"]
