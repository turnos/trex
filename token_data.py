import yaml
import pathlib

CONFIG_FILE_PATH = "/opt/trex/conf/token.yaml"

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
