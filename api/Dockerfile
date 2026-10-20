# Imagen del servicio de inferencia. Se construye desde la raíz del repositorio:
#   docker build -f api/Dockerfile -t g17/phishing-api:1.1 .
FROM python:3.13-slim

RUN useradd -m -u 1000 usuario
WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY --chown=usuario src/ src/
COPY --chown=usuario contracts/ contracts/
COPY --chown=usuario api/ api/

RUN mkdir -p /home/usuario/.cache/huggingface && chown -R usuario:usuario /home/usuario
USER usuario
ENV HOME=/home/usuario \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/usuario/.cache/huggingface

EXPOSE 7860
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "7860"]
