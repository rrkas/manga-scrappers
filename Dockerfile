FROM ubuntu:24.04

# set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONWARNINGS="ignore"
ENV PYTHONUNBUFFERED 1
ENV TZ=Asia/Kolkata

RUN apt update -y && apt upgrade -y && apt-get update -y && apt-get upgrade -y

RUN apt-get install -y python3 python3-full python3-pip python3-venv
RUN cp /usr/bin/python3 /usr/bin/python

RUN apt install -y ghostscript

WORKDIR /scrapper

COPY ./req.txt ./req.txt
RUN pip install -r req.txt --break-system-packages

COPY . .

CMD python collect.py


