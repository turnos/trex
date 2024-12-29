FROM python:3.13-alpine3.21

ARG CLIENT_ID
ARG CLIENT_SECRET
ARG LOG_LEVEL="INFO"

ENV CLIENT_ID=${CLIENT_ID} CLIENT_SECRET=${CLIENT_SECRET} LOG_LEVEL=${LOG_LEVEL}

VOLUME /conf

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

EXPOSE 5000

CMD [ "python", "./trex.py" ]