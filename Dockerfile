FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir --no-deps -r requirements.txt

COPY vrp vrp

ENV PYTHONPATH "${PYTHONPATH}:/app"
ENTRYPOINT [ "python", "vrp/run.py" ]