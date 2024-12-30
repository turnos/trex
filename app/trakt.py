import re
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(os.environ['LOG_LEVEL'])


def create_scrobble_object(plex_payload):
    result = {}
    if plex_payload["Metadata"]["type"] == "movie":
        movie = result["movie"] = {}
        ids = movie["ids"] = {}
        movie["title"] = plex_payload["Metadata"]["title"]
        movie["year"] = plex_payload["Metadata"]["year"]
        
        guids = str(plex_payload["Metadata"]["Guid"])
        logger.debug("Guids in payload:  %s", guids)
                
        imdb_id = search_imdb_id(guids)      
        if imdb_id:
            ids["imdb"] = imdb_id
            
        tmdb_id = search_tmdb_id(guids)
        if tmdb_id:
            ids["tmdb"] = tmdb_id
            
        logger.debug("movie ids: %s", ids)
        if not id:
            result = {}
            
    elif plex_payload["Metadata"]["type"] == "episode":
        show = result["show"] = {}
        show["title"] = plex_payload["Metadata"]["grandparentTitle"]
        show["ids"]["slug"] = plex_payload["grandparentSlug"]
        episode = result["episode"] = {}
        episode["title"] = plex_payload["Metadata"]["title"]
        episode["season"] = plex_payload["Metadata"]["parentIndex"]
        episode["number"] = plex_payload["Metadata"]["index"]
        ids = episode["ids"] = {}
        
        guids = str(plex_payload["Metadata"]["Guid"])
        
        logger.debug("Guids in payload:  %s", guids)
        
        tvdb_id = search_tvdb_id(guids)
        if tvdb_id:
            ids["tvdb"] = tvdb_id
        
        imdb_id = search_imdb_id(guids)      
        if imdb_id:
            ids["imdb"] = imdb_id
            
        tmdb_id = search_tmdb_id(guids)
        if tmdb_id:
            ids["tmdb"] = tmdb_id
        
        logger.debug("episode ids: %s", ids)
        if not ids:
            result = {}
        
    return result or None

def search_imdb_id(guid_str:str):
    imdb_match = re.search(r"imdb://(?P<imdb_id>tt\d+)", guid_str)        
    if imdb_match:
        return imdb_match.group("imdb_id")
    else:
        return None
    
def search_tmdb_id(guid_str:str):
    tmdb_match = re.search(r"tmdb://(?P<tmdb_id>\d+)", guid_str)        
    if tmdb_match:
        return int(tmdb_match.group("tmdb_id"))
    else:
        return None
    
def search_tvdb_id(guid_str:str):
    tvdb_match = re.search(r"tvdb://(?P<tvdb_id>\d+)", guid_str)
    if tvdb_match:
        return int(tvdb_match.group("tvdb_id"))
    else:
        return None