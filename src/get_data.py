import os
import sys
import inspect
import json
import pandas as pd
import numpy as np
import re

from paths import comtrade_data_path, get_api_key
from load_data import DataGetter



data_getter = DataGetter(
    _dir=comtrade_data_path,
    api_key=get_api_key()
)

    
class ComtradeData:
    def __init__(self, 
                 commodity_code: int | str,
                 period: int):
        
        self._period: int = period
        self._code: str = DataGetter.parse_commodity_code(commodity_code)
        self._commodity: str = DataGetter.commodity_code_desc(commodity_code)
        
        self._data: pd.DataFrame = data_getter.load(commodity_code, period)
        self._exports = None
        self._imports = None
        
    @property
    def period(self) -> int:
        return self._period
    
    @property
    def commodity_code(self) -> str:
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
    
    