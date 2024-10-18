FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir --no-deps -r requirements.txt
RUN pip config set global.index-url https://nexus.iquantex.com/repository/pypi/simple
RUN pip install --no-cache-dir --no-deps tools-vrp

ENTRYPOINT [ "vrp" ]