import urllib3
import requests
import json
import os
import re
import pandas as pd
import inspect

def dir_path():
    # Gets the directory where this function is called from
    frame = inspect.currentframe()
    filename = frame.f_code.co_filename
    return os.path.dirname(os.path.abspath(filename))


iso_map_file_path = os.path.join(dir_path(), "m49iso.json")
iso_to_name_map_file_path = os.path.join(dir_path(), "iso2name.json")
hscodes_file_path = os.path.join(dir_path(), "hscodes.json")


def create_m49iso_map():
    # Load metadata for M49 to ISO3 mapping
    meta_df = pd.read_csv(
        'https://raw.githubusercontent.com/DrPrettyman/CountryData/refs/heads/main/countries.csv', 
        keep_default_na=False
    )
    
    _d = meta_df[['m49_comtrade', 'iso3']].set_index('m49_comtrade').to_dict()['iso3']
    
    with open(iso_map_file_path, 'w') as _f:
        json.dump(_d, _f)
        
        
def create_iso2name_map():
    # Load metadata for M49 to ISO3 mapping
    meta_df = pd.read_csv(
        'https://raw.githubusercontent.com/DrPrettyman/CountryData/refs/heads/main/countries.csv', 
        keep_default_na=False
    )
    
    _d = meta_df[['iso3', 'country']].drop_duplicates().set_index('iso3').to_dict()['country']
    
    with open(iso_to_name_map_file_path, 'w') as _f:
        json.dump(_d, _f)
        

def load_m49iso_map() -> dict:
    if not os.path.exists(iso_map_file_path):
        create_m49iso_map()
        
    with open(iso_map_file_path, 'r') as _f:
        iso_map = json.load(_f)
        
    iso_map = {int(k): v for k, v in iso_map.items()}
        
    return iso_map


def load_iso2name_map() -> dict:
    if not os.path.exists(iso_to_name_map_file_path):
        create_iso2name_map()
        
    with open(iso_to_name_map_file_path, 'r') as _f:
        iso_map = json.load(_f)
        
    return iso_map


def fetch_commodity_codes():
    response = requests.get("https://comtradeapi.un.org/files/v1/app/reference/H2.json")
    response.raise_for_status()
    hscodes = json.loads(response.text)['results']
    hscodes.pop(0)
    for _record in hscodes:
        _record['simple_text'] = re.sub(r"^\d+[\-\s]+", "", _record['text']).lower()
        
    with open(hscodes_file_path, 'w') as _f:
        json.dump(hscodes, _f)
        
        
def load_commodity_codes():
    if not os.path.exists(hscodes_file_path):
        fetch_commodity_codes()
    
    with open(hscodes_file_path, 'r') as _f:
        _hscodes = json.load(_f)
        
    hscode_map = {
        _record['id']: _record['simple_text']
        for _record in _hscodes
    }

    hscode_text_map = {
        _record['simple_text']: _record['id']
        for _record in _hscodes
    }
        
    return hscode_map, hscode_text_map


hscode_map, hscode_text_map = load_commodity_codes()


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
        if c in hscode_map:
            return c
        c = "0"+c
        if c in hscode_map:
            return c
        raise ValueError(f"Invalid commodity code: {commodity_code}.")
    elif isinstance(commodity_code, str):
        if re.match(r'^\d+$', commodity_code):
            # If the commodity code is a string of digits, check if its in the list
            if commodity_code in hscode_map:
                return commodity_code
            ValueError(f"Invalid commodity code: {commodity_code}.")
        elif commodity_code.lower() in hscode_text_map:
            # If the commodity code is a string that matches a known commodity, get its code
            return hscode_text_map[commodity_code.lower()]
        else:
            raise ValueError(f"Invalid commodity code: {commodity_code}.")
    else:
        raise TypeError(f"Commodity code must be an int or str, got {type(commodity_code)}.")


def file_path(period: int, commodity_code: int | str) -> str:
    """
    Constructs the file path for the COMTRADE data based on the period and commodity code.
    
    Args:
        period (int): The year for which the data is fetched.
        commodity_code (int | str): The commodity code.

    Returns:
        str: The constructed file path.
    """
    commodity_code = parse_commodity_code(commodity_code)
    file_name = f'comtrade_{period}_{commodity_code}.json'
    
    return os.path.join(dir_path(), file_name)


def download_to_file(period: int, 
                     commodity_code: int | str,
                     key: str = None) -> int:
    """
    Fetches the COMTRADE data for a specific period.
    
    Args:
        period (int): The year for which to fetch the data.
        commodity_code (int): The commodity code to filter the data.

    Returns:
        pd.DataFrame: DataFrame containing the COMTRADE data.
    """
    if key is None:
        key = os.getenv('COMTRADE_API_KEY')

    commodity_code = parse_commodity_code(commodity_code)
    
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

    df.to_json(file_path(period, commodity_code), orient='records', indent=2)

    return 0


def fetch_data(period: int, 
               commodity_code: int | str,
               key: str = None) -> pd.DataFrame:
    """
    Fetches the COMTRADE data for a specific period 
    and returns it as a DataFrame.
    
    Args:
        period (int): The year for which to fetch the data. Default is 2023.
        
    Returns:
        pd.DataFrame: DataFrame containing the COMTRADE data.
    """
    
    _file_path = file_path(period, commodity_code)
    
    if not os.path.exists(_file_path):
        # If the file does not exist, download the data
        print(f"{os.path.basename(_file_path)} not found. Downloading data...")
        download_to_file(period, commodity_code, key)

    df = pd.read_json(_file_path)

    return df


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
    m49iso_map = load_m49iso_map()
    
    # Replace M49 codes with ISO3
    _df['exporter'] = _df['exporter_m49'].apply(m49iso_map.get)
    _df['partner'] = _df['partner_m49'].apply(m49iso_map.get)
    
    _df.drop(columns=['exporter_m49', 'partner_m49'], inplace=True)
        
    return _df
