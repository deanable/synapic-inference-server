FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/Synapic.Inference ./src/Synapic.Inference

EXPOSE 8080
ENTRYPOINT ["python", "src/Synapic.Inference/service.py"]
