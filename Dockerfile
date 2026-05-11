FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    libglib2.0-0 libnss3 \
    libfontconfig1 libxss1 libasound2 \
    libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .
RUN mkdir -p data exports

EXPOSE 7860

CMD ["honcho", "start"]
