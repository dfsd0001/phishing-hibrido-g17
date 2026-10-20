# Imagen de la interfaz web. Solo contiene la interfaz: no carga modelos y consulta la API.
#   docker build -t g17/phishing-ui:1.0 app
FROM python:3.13-slim

RUN useradd -m -u 1000 usuario
WORKDIR /home/usuario/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=usuario . .
USER usuario
ENV PYTHONUNBUFFERED=1

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
