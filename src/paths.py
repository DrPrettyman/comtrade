import os
import inspect
import json


comtrade_data_path = os.path.join(
        os.path.expanduser("~"),
        "Downloads",
        "comtrade"
    )
    
    
if not os.path.exists(comtrade_data_path):
    os.makedirs(comtrade_data_path)
    

plots_dir = os.path.join(comtrade_data_path, "plots")
if not os.path.exists(plots_dir):
    os.makedirs(plots_dir)
    
    
def dir_path() -> str:
    # Gets the directory where this function is called from
    frame = inspect.currentframe()
    filename = frame.f_code.co_filename
    return os.path.dirname(os.path.abspath(filename))


def get_secrets() -> dict:
    secrets_path = os.path.join(
        os.path.dirname(dir_path()),
        ".secrets.json"
    )
    
    with open(secrets_path, "r") as _f:
        s = json.load(_f)
    
    return s


def set_api_key(key: str = None):
    os.environ['COMTRADE_API_KEY'] = key


def get_api_key():
    s = get_secrets()
    if 'COMTRADE_API_KEY' in s:
        key = s['COMTRADE_API_KEY']
        os.environ['COMTRADE_API_KEY'] = key
        
    key = os.environ.get('COMTRADE_API_KEY')
    if key is None:
        raise ValueError('No key provided')
    
    return key