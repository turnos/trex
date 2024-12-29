import re
import time

from flask import Flask, request, json
from token_data import *
import requests
import os
import threading


app = Flask(__name__)
logger = app.logger

LOG_LEVEL = os.environ['LOG_LEVEL']
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
TRAKT_API_URL = "https://api.trakt.tv/"
SCROBBLE_START = "scrobble/start"
SCROBBLE_PAUSE = "scrobble/pause"
SCROBBLE_STOP = "scrobble/stop"
OAUTH_TOKEN = "oauth/token"
OAUTH_DEVICE_TOKEN = "oauth/device/token"
OAUTH_DEVICE_CODE = "oauth/device/code"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
HEADERS = {"trakt-api-version": "2", "trakt-api-key": CLIENT_ID}


def run():
    app.logger.setLevel(LOG_LEVEL)
    app.run(host="0.0.0.0")

@app.route("/trakt_hook", methods=["POST"])
def hook_receiver():
    payload = json.loads(request.form["payload"])
    # Let's only handle the scrobble event for now.
    if payload["event"] != "media.scrobble":
        logger.debug("payload is not scrobble: " + str(payload))
        return ""
    
    if is_valid() and is_expired():
        refresh_token()
    elif not is_valid():
        return "App is not authenticated with trakt. Please initialize authentication first on /auth", 400
    
    scrobble_object = create_scrobble_object(payload)
    if not scrobble_object:
        logger.info("Unable to form trakt request from payload: " + str(payload["Metadata"]))
        return "Unable to form trakt request.", 500
    
    scrobble_object.update({
        "progress": 100,
    })
    logger.debug("Scrobble-Object: %s", scrobble_object)
    
    headers = {"Authorization": "Bearer {}".format(get_access_token())}
    headers.update(HEADERS)
    response = requests.post(TRAKT_API_URL + SCROBBLE_STOP, json=scrobble_object, headers=headers)
    logger.info("Trakt.tv response code: %d", response.status_code)
    logger.debug("Trakt.tv Response: %s", response)
    return ""


def create_scrobble_object(plex_payload):
    result = {}
    if plex_payload["Metadata"]["type"] == "movie":
        movie = result["movie"] = {}
        movie["title"] = plex_payload["Metadata"]["title"]
        movie["year"] = plex_payload["Metadata"]["year"]
        imdb_match = re.match(
            r"imdb://(?P<imdb_id>tt\d+)", plex_payload["Metadata"]["Guid"]
        )
        if imdb_match:
            movie["ids"] = {"imdb": imdb_match.group("imdb_id")}
    elif plex_payload["Metadata"]["type"] == "episode":
        episode = result["episode"] = {}
        ids = episode["ids"] = {}
        episode["title"] = plex_payload["Metadata"]["title"]
        
        tvdb_match = re.match(r"tvdb://(?P<tvdb_id>\d+)", plex_payload["Metadata"]["Guid"])
        
        imdb_match = re.match(r"imdb://(?P<imdb_id>tt\d+)", plex_payload["Metadata"]["Guid"])

        if tvdb_match:
            ids.update({"tvdb": int(tvdb_match.group("tvdb_id"))})
        
        if imdb_match:
            ids.update({"imdb": imdb_match.group("imdb_id")})
            
        if not tvdb_match and not imdb_match:
            result = {}
        
    return result or None



@app.route("/auth", methods=["GET"])
def authenticate():
    logger.info("Start app registration.")
    request_body = {"client_id": CLIENT_ID}
    try:
        r = requests.post(TRAKT_API_URL + OAUTH_DEVICE_CODE, data=request_body).json()

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

        r = requests.post(TRAKT_API_URL + OAUTH_DEVICE_TOKEN, data=request_body)
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

def refresh_token():
    logger.info("Refresh token")
    request_body = {
        "refresh_token": get_refresh_token(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "refresh_token" 
    }
    try:
        r = requests.post(TRAKT_API_URL + OAUTH_TOKEN, data=request_body).json()
        logger.debug("Received response: %s", r)
        save_token_data(r)
        logger.info("Saved new token")
        return True
    except requests.RequestException as e:
        logger.exception("Failed to refresh token", e)
    return False
    
if __name__ == "__main__":
    run()
