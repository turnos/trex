import yaml
import pathlib
import time

CONFIG_FILE_PATH = "/conf/token.yaml"

def load_token_data():
    configfile = pathlib.Path(CONFIG_FILE_PATH)
    with configfile.open('r') as f:
        return yaml.safe_load(f.read())


def save_token_data(config):
    configfile = pathlib.Path(CONFIG_FILE_PATH)
    with configfile.open('w') as f:
        return yaml.dump(config, f, default_flow_style=False)
    
def get_access_token():
    token_data = load_token_data()
    return token_data['access_token']
    
def get_refresh_token():
    token_data = load_token_data()
    return token_data['refresh_token']

def is_valid():
    token_data = load_token_data()
    if 'access_token' not in token_data:
        return False
    return True

def is_expired():
    token_data = load_token_data()
    
    expiration_time = (int(token_data['expires_in']) + int(token_data['created_at'])) * 1000
    current_time = (int(time.time()) * 1000) + 10000 # add 10 seconds to account for time drift
    
    if current_time > expiration_time:
        return True
    return False
    
