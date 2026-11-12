FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core fonts-dejavu-core libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi8 libjpeg62-turbo libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /srv/app/data && useradd --uid 10001 --create-home certigov \
    && chown -R certigov:certigov /srv/app
USER certigov
EXPOSE 10000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--proxy-headers","--forwarded-allow-ips","127.0.0.1"]
