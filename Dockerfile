FROM python:3.14.2-alpine3.23

RUN apk update && apk upgrade --no-cache

ENV PYTHONUNBUFFERED=1 \
PIP_NO_CACHE_DIR=1 \
PATH=/usr/local/bin:$PATH

RUN addgroup -S devops && adduser -S devops -G devops

WORKDIR /usr/src/app

RUN chown -R devops:devops /usr/src/app

RUN apk add --no-cache \
    libstdc++ \
    && rm -rf /var/cache/apk/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY main.py .

USER devops

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
