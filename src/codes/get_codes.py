"""
Loads various json files as dict objects to map various coded values.

codes.m49_to_iso:   maps Comtrade m49 country codes to ISO-alpha3 code.
codes.iso_to_name:  maps ISO-alpha3 to name. E.g. "FRA" -> "France"
codes.hs_to_desc:   maps HS commodity codes to a description. E.g. "2204" -> "wine"
codes.desc_to_hs:   maps the other way
"""


import os
import json
import re
import inspect
import requests
import pandas as pd


def dir_path() -> str:
    # Gets the directory where this function is called from
    frame = inspect.currentframe()
    filename = frame.f_code.co_filename
    return os.path.dirname(os.path.abspath(filename))


class JsonFiles:
    class File:
        def __init__(self, _file_path):
            self._file_path = _file_path
            
        def exists(self):
            return os.path.exists(self._file_path)
        
        def load(self):
            with open(self._file_path, 'r') as _f:
                _data = json.load(_f)
            return _data
        
        def write(self, data: list | dict):
            with open(self._file_path, 'w') as _f:
                json.dump(data, _f)
        
    def __init__(self, _dir: str):
        self._dir = _dir
        if not os.path.exists(self._dir):
            os.makedirs(self._dir)
            
    def add(self, file_name: str):
        _file = ".".join([file_name, "json"])
        _path = os.path.join(self._dir, _file)
        self.__setattr__(file_name, self.File(_path))
      
    
class MetaData:
    def __init__(self, _dir):
        self.files = JsonFiles(_dir)
        self.files.add("m49_to_iso")
        self.files.add("iso_to_name")
        self.files.add("hscodes")
        
        self._country_data = None
        
        self._m49_to_iso = None
        self._iso_to_name = None
        self._hs_to_desc = None
        self._desc_to_hs = None
        
    def _get_country_data(self):
        if self._country_data is None:
            self._country_data = pd.read_csv(
                'https://raw.githubusercontent.com/DrPrettyman/CountryData/refs/heads/main/countries.csv', 
                keep_default_na=False
            )
        return self._country_data
    
    def _download_m49_to_iso(self):
        # Load metadata for M49 to ISO3 mapping
        meta_df = self._get_country_data()
        
        _d = meta_df[['m49_comtrade', 'iso3']].set_index('m49_comtrade').to_dict()['iso3']
        
        self.files.m49_to_iso.write(_d)
        
    def _download_iso_to_name(self):
        # Load metadata for ISO3 to Country name mapping
        meta_df = self._get_country_data()
        
        _d = meta_df[['iso3', 'country']].drop_duplicates().set_index('iso3').to_dict()['country']
        
        self.files.iso_to_name.write(_d)
          
    def _download_hscodes(self):
        response = requests.get("https://comtradeapi.un.org/files/v1/app/reference/H2.json")
        response.raise_for_status()
        hscodes = json.loads(response.text)['results']
        hscodes.pop(0)
        for _record in hscodes:
            _record['simple_text'] = re.sub(r"^\d+[\-\s]+", "", _record['text']).lower()
            
        self.files.hscodes.write(hscodes)
  
    def _get_m49_to_iso(self) -> dict:
        if not self.files.m49_to_iso.exists():
            self._download_m49_to_iso()
 
        iso_map = self.files.m49_to_iso.load()
            
        return {int(k): v for k, v in iso_map.items()}
    
    def _get_iso_to_name(self):
        if not self.files.iso_to_name.exists():
            self._download_iso_to_name()
        
        return self.files.iso_to_name.load()
    
    def _get_hs_to_desc(self):
        if not self.files.hscodes.exists():
            self._download_hscodes()
            
        _hscodes = self.files.hscodes.load()
        
        return {
            _record['id']: _record['simple_text']
            for _record in _hscodes
        }
        
    def _get_desc_to_hs(self):
        if not self.files.hscodes.exists():
            self._download_hscodes()
            
        _hscodes = self.files.hscodes.load()
        
        return {
            _record['simple_text']: _record['id']
            for _record in _hscodes
        }
      
    @property
    def m49_to_iso(self):
        if self._m49_to_iso is None:
            self._m49_to_iso = self._get_m49_to_iso()
        return self._m49_to_iso

    @property
    def iso_to_name(self):
        if self._iso_to_name is None:
            self._iso_to_name = self._get_iso_to_name()
        return self._iso_to_name

    @property
    def hs_to_desc(self):
        if self._hs_to_desc is None:
            self._hs_to_desc = self._get_hs_to_desc()
        return self._hs_to_desc

    @property
    def desc_to_hs(self):
        if self._desc_to_hs is None:
            self._desc_to_hs = self._get_desc_to_hs()
        return self._desc_to_hs
    
    
codes = MetaData(_dir=dir_path())