FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN chmod +x /app/cloud-entrypoint.sh
EXPOSE 8787 8790-8801
CMD ["bash", "/app/cloud-entrypoint.sh"]