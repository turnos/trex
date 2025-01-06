import re
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(os.environ['LOG_LEVEL'])


def create_scrobble_object(plex_payload):
    result = {}
    metadata = plex_payload["Metadata"]
    logger.debug("Metadata: %s", metadata)
    if metadata["type"] == "movie":
        movie = result["movie"] = {}
        ids = movie["ids"] = {}
        movie["title"] = metadata["title"]
        movie["year"] = metadata["year"]
        
        guids = str(metadata["Guid"])
        logger.debug("Guids in payload:  %s", guids)
                
        imdb_id = search_imdb_id(guids)      
        if imdb_id:
            ids["imdb"] = imdb_id
            
        tmdb_id = search_tmdb_id(guids)
        if tmdb_id:
            ids["tmdb"] = tmdb_id
            
        logger.debug("movie ids: %s", ids)
            
    elif metadata["type"] == "episode":
        show = result["show"] = {}

        if "grandparentSlug" in metadata:
            show_ids = show["ids"] = {}
            show_ids["slug"] = metadata["grandparentSlug"]
        
        show["title"] = metadata["grandparentTitle"]

        episode = result["episode"] = {}
        episode["title"] = metadata["title"]
        episode["season"] = metadata["parentIndex"]
        episode["number"] = metadata["index"]
        ids = episode["ids"] = {}
        
        guids = str(metadata["Guid"])
        
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