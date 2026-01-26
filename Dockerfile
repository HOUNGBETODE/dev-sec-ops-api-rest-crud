FROM python:3.14

RUN apt-get update && apt-get upgrade -y

RUN useradd -m devops
RUN mkdir -p /usr/src/app && chown -R devops:devops /usr/src/app

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

USER devops

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
