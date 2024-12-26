# Trex 
Small script which can handle Plex scrobble webhooks and log them to trakt.

## Docker
### Env params
| Name | Value |
| --- | --- |
| CLIENT_ID | Your Trakt.tv App CLIENT_ID |
| CLIENT_SECRET | Your Trakt.tv App CLIENT_SECRET |

### Run example
```
docker run --name Trex -d \
	-p 5000:5000 \
	--env 'CLIENT_ID=<your_client_id>' \
	--env 'CLIENT_SECRET=<your_client_secret>' \
	--volume /mnt/cache/appdata/trex:/conf \
	turnos/trex
```

## Usage

Authenticate your docker instance for using the trakt.tv API `http://<your server>:5000/auth`.
Starts authentication to trakt.tv and records the oauth token in trex configfile. Follow the instructions to complete the authentication.

Add a new webhook to Plex with the url `http://<your server>:5000/trakt_hook`  


Forked from [gazpachoking/trex](https://github.com/gazpachoking/trex)
