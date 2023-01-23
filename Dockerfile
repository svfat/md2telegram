FROM python:3.10.5
WORKDIR /
RUN apt-get -y update
RUN apt-get update && apt-get install -y python3 python3-pip
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
COPY . . 
CMD python3 bot.py
