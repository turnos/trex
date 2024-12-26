FROM python:3.13-alpine3.21

ARG CLIENT_ID
ARG CLIENT_SECRET

VOLUME /conf

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD [ "python", "./trex.py" ]