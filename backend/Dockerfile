FROM python:3.13-slim

WORKDIR /app

ARG SOURCE_REVISION=untracked
ENV MLECC_SOURCE_REVISION=${SOURCE_REVISION}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /storage \
    && chown -R appuser:appuser /app /storage
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
