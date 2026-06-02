FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 浏览器
RUN playwright install chromium && playwright install-deps chromium

# 应用代码
COPY . .

# 数据目录
RUN mkdir -p /app/data /app/data/uploads

EXPOSE 8000

CMD ["python", "start.py"]
