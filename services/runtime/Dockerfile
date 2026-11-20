FROM python:3.12-slim
WORKDIR /app
COPY . .
EXPOSE 8787 8790-8801
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health',timeout=2)" || exit 1
