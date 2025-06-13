import os
import sys
import inspect
import urllib3
import requests
import json
import pandas as pd
import numpy as np
import re
   
from codes.get_codes import codes
    
    
class DataGetter:
    @staticmethod
    def parse_commodity_code(commodity_code: int | str) -> str:
        """
        Parses the commodity code to ensure it is an integer.
        
        Args:
            commodity_code (int | str): The commodity code to parse.

        Returns:
            int: The parsed commodity code.
        """
        if isinstance(commodity_code, int):
            # If the commodity code is an integer, check if it's in the list
            # if not, add a leading zero and check that
            c = str(commodity_code)
            if c in codes.hs_to_desc:
                return c
            c = "0"+c
            if c in codes.hs_to_desc:
                return c
            raise ValueError(f"Invalid commodity code: {commodity_code}.")
        elif isinstance(commodity_code, str):
            if re.match(r'^\d+$', commodity_code):
                # If the commodity code is a string of digits, check if its in the list
                if commodity_code in codes.hs_to_desc:
                    return commodity_code
                ValueError(f"Invalid commodity code: {commodity_code}.")
            elif commodity_code.lower() in codes.desc_to_hs:
                # If the commodity code is a string that matches a known commodity, get its code
                return codes.desc_to_hs[commodity_code.lower()]
            else:
                raise ValueError(f"Invalid commodity code: {commodity_code}.")
        else:
            raise TypeError(f"Commodity code must be an int or str, got {type(commodity_code)}.")
        
    @staticmethod
    def commodity_code_desc(commodity_code: int | str) -> str:
        _c = DataGetter.parse_commodity_code(commodity_code)
        return codes.hs_to_desc[_c]
    
    def __init__(self, _dir: str, api_key: str = None):
        self._dir = _dir
        self._key = api_key
        
    def set_api_key(self, api_key: str):
        self._key = api_key
        
    def _commodity_dir(self, commodity_code: int | str):
        _c = self.parse_commodity_code(commodity_code)
        _p = os.path.join(
            self._dir, 
            f"hs{_c}"
        )
        if not os.path.exists(_p):
            os.makedirs(_p)
        return _p
    
    def file(self, commodity_code: int | str, period: int) -> str:
        _p = os.path.join(
            self._commodity_dir(commodity_code),
            f"annual{period}.json"
        )
        return _p
        
    def file_exists(self, commodity_code: int | str, period: int) -> bool:
        return os.path.exists(self.file(commodity_code, period))
    
    @staticmethod
    def tidy_annual_export_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        The raw comtrade data contains multiple rows for each exporter-partner pair,
        with different quantities and values. This function aggregates the data
        by taking the maximum quantity and value for each exporter-partner pair.
        It also renames the columns to more descriptive names and removes rows
        where either the exporter or partner M49 code is 0 (representing "World").
        The resulting DataFrame contains unique exporter-partner pairs with their
        corresponding maximum quantity and value.
        
        Args:
            df (pd.DataFrame): DataFrame containing the COMTRADE data.

        Returns:
            pd.DataFrame: DataFrame with aggregated data.
        """
        _df = df[["reporterCode", "partnerCode", "qty", "primaryValue"]].rename(
            columns={
                "reporterCode": "exporter_m49",
                "partnerCode": "partner_m49",
                "qty": "quantity",
                "primaryValue": "value"
            }
        ).groupby(
            ["exporter_m49", "partner_m49"]
        ).agg(
            {
                "quantity": "max",
                "value": "max"
            }
        ).reset_index()

        # Drop rows where either exporter or partner M49 code is 0 ("World")
        _df = _df[(_df["exporter_m49"] != 0) & (_df["partner_m49"] != 0)].sort_values(
            by=["exporter_m49", "partner_m49"]
        ).reset_index(drop=True)
        
        # Load metadata for M49 to ISO3 mapping
        m49iso_map: dict = codes.m49_to_iso
        
        # Replace M49 codes with ISO3
        _df['exporter'] = _df['exporter_m49'].apply(m49iso_map.get)
        _df['partner'] = _df['partner_m49'].apply(m49iso_map.get)
        
        _df.drop(columns=['exporter_m49', 'partner_m49'], inplace=True)
            
        return _df
        
    def _download_data(self, 
                     commodity_code: int | str,
                     period: int) -> int:
        """
        Fetches the COMTRADE data for a specific period.
        
        Args:
            commodity_code (int): The HS commodity code to filter the data.
            period (int): The year for which to fetch the data.
            
        Returns:
            pd.DataFrame: DataFrame containing the COMTRADE data.
        """
        if self._key is None:
            key = get_api_key()
        else:
            key = self._key

        commodity_code = self.parse_commodity_code(commodity_code)
        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Initialize the HTTP connection pool
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        
        response = http.request(
            method='GET', 
            url="https://comtradeapi.un.org/data/v1/get/C/A/HS", 
            headers={
                'Cache-Control': 'no-cache',
                'Ocp-Apim-Subscription-Key': key,
            },
            fields={
                'cmdCode': f'{commodity_code}',
                'flowCode': 'X',
                'period': f'{period}',
                'includeDesc': 'false'
            }
        )
        
        if response.status != 200:
            raise Exception(f"Error fetching data: {response.status}")
        
        data = json.loads(response.data.decode('utf-8'))
        
        df = pd.DataFrame(data['data'])
        if df.empty:
            raise ValueError("No data returned for the specified period.")
        
        df = self.tidy_annual_export_data(df)

        df.to_json(self.file(commodity_code, period), orient='records', indent=2)

        return 0
    
    def load(self, commodity_code: int | str, period: int) -> pd.DataFrame:
        """
        Fetches the COMTRADE data for a specific period 
        and returns it as a DataFrame.
        
        Args:
            commodity_code (int): The HS commodity code to filter the data.
            period (int): The year for which to fetch the data.
            
        Returns:
            pd.DataFrame: DataFrame containing the COMTRADE data.
        """
        
        if not self.file_exists(commodity_code, period):
            self._download_data(commodity_code, period)

        return pd.read_json(self.file(commodity_code, period))
    