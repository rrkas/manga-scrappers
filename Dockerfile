FROM ubuntu:22.04

# set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONWARNINGS="ignore"
ENV PYTHONUNBUFFERED 1
ENV TZ=Asia/Kolkata

RUN apt-get update -y && apt-get upgrade -y && \
    apt update -y && apt upgrade -y

RUN apt-get install -y python3 python3-full python3-pip python3-venv

RUN cp /usr/bin/python3 /usr/bin/python

WORKDIR /scrapper

COPY req.txt ./

RUN pip install -U -r ./req.txt

COPY . .

CMD python collect.py

