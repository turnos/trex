FROM python:3.13-alpine3.21

ARG CLIENT_ID
ARG CLIENT_SECRET
ENV ENV_CLIENT_ID $CLIENT_ID
ENV ENV_CLIENT_SECRET $CLIENT_SECRET

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./trex.py" ]