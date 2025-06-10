import os
import sys
import inspect
import json
import pandas as pd
import numpy as np
import re

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
    if key is None:
        s = get_secrets()
        if 'COMTRADE_API_KEY' not in s:
            raise ValueError('No key provided')
        key = s['COMTRADE_API_KEY']
    os.environ['COMTRADE_API_KEY'] = key
    

def data_module_path() -> str:
    p = dir_path()
    dp = None
    while len(p) > 1:
        if "comtrade_data" in os.listdir(p):
            dp = os.path.join(p, "comtrade_data")
            break
        p = os.path.dirname(p)
    
    if dp is None:
        raise FileNotFoundError
    
    return dp
    
    
sys.path.append(data_module_path())
import fetch_data
iso2name_map = fetch_data.load_iso2name_map()


class ComtradeData:
    def __init__(self, 
                 period: int, 
                 commodity_code: int | str,
                 key: str = None):
        
        self._period = period
        self._code = fetch_data.parse_commodity_code(commodity_code)
        self._commodity = fetch_data.hscode_map[self._code]
        
        set_api_key(key)
        
        comtrade_df = fetch_data.fetch_data(period, commodity_code)
        comtrade_df = fetch_data.tidy_annual_export_data(comtrade_df)
        
        self._data = comtrade_df
        self._exports = None
        self._imports = None
        
    @staticmethod
        
    @property
    def period(self):
        return self._period
    
    @property
    def commodity_code(self):
        return self._code
    
    @property
    def all(self) -> pd.DataFrame:
        return self._data
    
    def set_exports(self):
        exports_agg = self.all.sort_values(
            by=['exporter', 'value'],
            ascending=[True, False]    
        ).groupby('exporter').agg(
            value=('value', 'sum'),
            quantity=('quantity', 'sum'),
            top5_partners=('partner', lambda x: x.head(5).tolist())
        ).reset_index().rename(
            columns={'exporter': 'country'}
        )

        exports_agg['log_value'] = np.log10(exports_agg['value'] + 1)  # +1 to handle zeros

        self._exports = exports_agg
        
    def set_imports(self):
        imports_agg = self.all.sort_values(
            by=['partner', 'value'],
            ascending=[True, False]    
        ).groupby('partner').agg(
            value=('value', 'sum'),
            quantity=('quantity', 'sum'),
            top5_partners=('exporter', lambda x: x.head(5).tolist())
        ).reset_index().rename(
            columns={'partner': 'country'}
        )

        imports_agg = imports_agg[imports_agg['country'].apply(lambda code: re.match(r'^[A-Z]{3}$', code) is not None)]

        imports_agg['log_value'] = np.log10(imports_agg['value'] + 1)  # +1 to handle zeros
        
        self._imports = imports_agg
        
    @property
    def exports(self) -> pd.DataFrame:
        if self._exports is None:
            self.set_exports()
        return self._exports
    
    @property
    def imports(self) -> pd.DataFrame:
        if self._imports is None:
            self.set_imports()
        return self._imports
    
    