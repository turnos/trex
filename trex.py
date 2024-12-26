import pathlib
import re
import time

import click
from flask import Flask, request, json
import requests
import yaml
import os
import threading


app = Flask(__name__)
logger = app.logger

VERSION = "0.9"
TRAKT_API_URL = "https://api.trakt.tv/"
SCROBBLE_START = "scrobble/start"
SCROBBLE_PAUSE = "scrobble/pause"
SCROBBLE_STOP = "scrobble/stop"
CLIENT_ID = os.environ['ENV_CLIENT_ID'] #"5c22e26bdacc760154ce141ce201424be373cfc9fafd0e987953e99b5d1df5e4"
CLIENT_SECRET = os.environ['ENV_CLIENT_SECRET'] #"614a2d5856d44e6fb8791c7ddcef9764d044d385965cfa86479430d02d422a2b"
CONFIG_FILE_PATH = "./conf/token.yaml"
HEADERS = {"trakt-api-version": "2", "trakt-api-key": CLIENT_ID}



def run():
    app.run(host="0.0.0.0")

@app.route("/trakt_hook", methods=["POST"])
def hook_receiver():
    config = load_config()
    payload = json.loads(request.form["payload"])
    # Let's only handle the scrobble event for now.
    if payload["event"] != "media.scrobble":
        return ""
    access_token = config["access_token"]
    if not access_token:
        return "App is not authenticated with trakt. Please initialize authentication first on /auth"
    scrobble_object = create_scrobble_object(payload)
    if not scrobble_object:
        return "Unable to form trakt request.", 500
    scrobble_object.update({
        "progress": 100,
        "app_version": VERSION,

    })
    headers = {"Authorization": "Bearer {}".format(access_token)}
    headers.update(HEADERS)
    requests.post(
        TRAKT_API_URL + SCROBBLE_STOP,
        json=scrobble_object,
        headers=headers
    )
    return ""


def create_scrobble_object(plex_payload):
    result = {}
    if plex_payload["Metadata"]["type"] == "movie":
        movie = result["movie"] = {}
        movie["title"] = plex_payload["Metadata"]["title"]
        movie["year"] = plex_payload["Metadata"]["year"]
        imdb_match = re.match(
            r"imdb://(?P<imdb_id>tt\d+)", plex_payload["Metadata"]["guid"]
        )
        if imdb_match:
            movie["ids"] = {"imdb": imdb_match.group("imdb_id")}
    elif plex_payload["Metadata"]["type"] == "episode":
        show = result["show"] = {}
        episode = result["episode"] = {}
        show["title"] = plex_payload["Metadata"]["grandparentTitle"]
        episode["title"] = plex_payload["Metadata"]["title"]
        tvdb_match = re.match(
            r"thetvdb://(?P<tvdb_id>\d+)/(?P<season>\d+)/(?P<episode>\d+)",
            plex_payload["Metadata"]["guid"],
        )
        if tvdb_match:
            show["ids"] = {"tvdb": int(tvdb_match.group("tvdb_id"))}
            episode["season"] = int(tvdb_match.group("season"))
            episode["number"] = int(tvdb_match.group("episode"))
        else:
            episode["season"] = plex_payload["Metadata"]["parentIndex"]
            episode["number"] = plex_payload["Metadata"]["index"]
    return result or None


def load_config():
    configfile = pathlib.Path(CONFIG_FILE_PATH)
    with configfile.open('r') as f:
        return yaml.safe_load(f.read())


def save_token_data(config):
    configfile = pathlib.Path(CONFIG_FILE_PATH)
    with configfile.open('w') as f:
        return yaml.dump(config, f, default_flow_style=False)

@app.route("/auth", methods=["GET"])
def authenticate():
    logger.info("Start app registration.")
    request_body = {"client_id": CLIENT_ID}
    try:
        r = requests.post(TRAKT_API_URL + "oauth/device/code", data=request_body).json()

        logger.debug("Received response %s", r)
        user_code = r["user_code"]
        verification_url = r["verification_url"]
        device_code = r["device_code"]
        interval = r["interval"]
        expires_in = r["expires_in"]

        expires_in_min = expires_in / 60
        logger.info(
            "Received user_code %s. Code expires in %d minutes. User needs to authenticate device on %s",
            user_code,
            expires_in_min,
            verification_url,
        )

        threading.Thread(
            target=poll_auth_status,
            name="Authorization_Polling",
            args=(device_code, interval, time.time() + expires_in),
        ).start()
        logger.info("Started background polling for authorization status")

        response = f'Please visit <a href="{verification_url}/{user_code}">{verification_url}</a> and use code {user_code} to authenticate this app on trakt.tv within the next {expires_in_min} minutes.'
        logger.debug("Send response to user: %s", response)
        return response
    except requests.RequestException as e:
        logger.exception("Device authorization with trakt.tv failed: ", e)
    return ""

def poll_auth_status(device_code, interval, end_time):
    logger.info("Start polling for authorization..")

    request_body = {
        "code": device_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    logger.debug("Construct request body: %s", request_body)

    while time.time() < end_time:
        logger.info("Wait %d seconds before polling authorization status", interval)
        time.sleep(interval)

        r = requests.post(TRAKT_API_URL + "oauth/device/token", data=request_body)
        result = None

        if r.status_code == 200:
            logger.info("Authorization successful!")
            result = r.json()
            logger.debug("Received response %s", result)
            break
        elif r.status_code == 400:
            logger.info("Waiting for user to register device")
        elif r.status_code == 404:
            logger.error(
                "Device_code %s is not known to trakt.tv. Authorization failed, stop polling.",
                device_code,
            )
            break
        elif r.status_code == 409:
            logger.info(
                "Device_code %s is already registered, stop polling", device_code
            )
            break
        elif r.status_code == 410:
            logger.info("Authorization request expired. Restart Authorization process")
            break
        elif r.status_code == 418:
            logger.info("User denied this device. Stop polling.")
            break
        elif r.status_code == 429:
            logger.warning("Polling is too fast, increasing interval by 1 second")
            interval += 1

    if not result:
        logger.error("Failed to poll authorization status, please try again")
        return

    save_token_data(result)
    logger.info("Saved token data")
    return ""

def refresh_token(token_data):
    logger.info("Refresh token")
    request_body = {
        "refresh_token": token_data['refresh_token'],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "refresh_token" 
    }
    try:
        r = requests.post(TRAKT_URL + "oauth/token", data=request_body).json()
        logger.debug("Received response: %s", r)
        save_token_data(r)
        logger.info("Saved new token")
        return True
    except requests.RequestException as e:
        logger.exception("Failed to refresh token", e)
        
    return False

if __name__ == "__main__":
    run()
