FROM python:3.13-alpine

RUN addgroup -S devops && adduser -S devops -G devops

WORKDIR /usr/src/app

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
