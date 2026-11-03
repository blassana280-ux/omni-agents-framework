# Cyber Force 100 — image d'exécution (défensive, minimale)
# Construire depuis la racine du dossier cyber-force-100/ :
#   docker build -t cf100:0.2.0 .
# Exécuter (API sur le port 8100) :
#   docker run --rm -p 8100:8100 -e CF100_API_TOKEN=... cf100:0.2.0
FROM python:3.11-slim

# Durcissement : pas de shell de connexion d'agent, répertoire propre.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances d'abord (cache Docker), puis le package.
COPY pyproject.toml README.md ./
COPY cf100 ./cf100
COPY registry ./registry
RUN pip install ".[api]"

# Utilisateur non privilégié — moindre privilège jusqu'au conteneur.
RUN useradd --system --create-home --shell /usr/sbin/nologin cf100
RUN mkdir -p /app/data && chown -R cf100:cf100 /app
USER cf100

EXPOSE 8100

# Santé de l'API ; données persistantes à monter en volume (/app/data).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8100/health') \
.status == 200 else 1)" || exit 1

CMD ["uvicorn", "cf100.api.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8100"]
