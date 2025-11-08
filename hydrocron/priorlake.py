"""
Functions for interacting with the Hydrocron API for PriorLake products.\n

note::
Due to a new version (D) for PriorLake products, this module only works for products in version C.
This may include PLD lake_id numbers as version D uses PLD v2.02. This also impacts time ranges,
you may only recieve data from 2023 up to May 2025.

todo::
    - Finish get_records function for multiple site fetching.
"""

from typing import Union, Optional, Literal, List, Tuple
from datetime import datetime

import concurrent.futures as cf
import geopandas as gpd
import pandas as pd

import os
import io
import time
import requests

BASE_URL = "https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/timeseries?feature=PriorLake"
PRIOR_LAKE_FIELDS = [ # As of 9/30/25 [Source: Hydrocron API Docs after personal testing]
        'lake_id', 'reach_id', 'obs_id', 'overlap', 'n_overlap',
        'time', 'time_tai', 'time_str', 'wse', 'wse_u', 'wse_r_u', 'wse_std',
        'area_total', 'area_tot_u', 'area_detct', 'area_det_u',
        'layovr_val', 'xtrk_dist', 'ds1_l', 'ds1_l_u', 'ds1_q', 'ds1_q_u',
        'ds2_l', 'ds2_l_u', 'ds2_q', 'ds2_q_u',
        'quality_f', 'dark_frac', 'ice_clim_f', 'ice_dyn_f', 'partial_f',
        'xovr_cal_q', 'geoid_hght', 'solid_tide', 'load_tidef', 'load_tideg', 'pole_tide',
        'dry_trop_c', 'wet_trop_c', 'iono_c', 'xovr_cal_c', 'lake_name', 'p_res_id',
        'p_lon', 'p_lat', 'p_ref_wse', 'p_ref_area', 'p_date_t0', 'p_ds_t0', 'p_storage',
        'cycle_id', 'pass_id', 'continent_id', 'range_start_time', 'range_end_time',
        'crid', 'geometry', 'PLD_version', 'collection_shortname'
    ]

def call_pl( # Call PriorLake API
        site: Union[int, str] = None, 
        time_range: Tuple[str, str] = None,
        fields: Optional[List[str]] = None, 
        return_geo: bool = False, 
        ) -> requests.Response:
    """
    Call Prior Lake API.\n
    Fetches Hydrocron API for a specific Feature ID (site) within "PriorLake" and returns json response.

    .. note::
        'site' and 'time_range' are required parameters.\n
        'time_range' can accept both 'YYYY-MM-DD' and ISO 8601 (UTC) format (see parameters for example). Other formats could result in bugs\n        
        'fields' will be filled with all available fields [as of 9/30/25] if None.\n
        If you are querying 1 field it NEEDS to be in a list, e.g. fields=['quality_f'].\n
   
    Parameters
    ----------
        site : int  or string, required
            Site ID to query. (known as lake_id in PLD)
            Ex: '67890' or 67890
        time_range : tuple of strings, required
            Start and end time in 'YYYY-MM-DD' or ISO 8601 (UTC) format. 
            Ex: ('2023-12-22', '2024-08-17') or ('2023-12-22T22:45:23Z', '2024-08-17T11:30:00Z')
        fields : list of strings or None, optional, default None
            Fields to query within the service. If None, defaults to all fields for the
            service. Ex: ['time', 'wse', 'area_total'] or ['geometry'] or None
        return_geo : bool, optional, default False
            If True, returns json:geojson request. Otherwise, returns json:csv request.

    Returns
    -------
        response : requests.Response 
            API response object containing json response.
    """
    # === Evaluate Inputs ===
    # Format time_range
    formatted_time = []
    for time_str in time_range:
        try:
            time_obj = datetime.strptime(time_str, "%Y-%m-%d")
            formatted_time.append(time_obj.strftime("%Y-%m-%dT00:00:00Z"))
        except ValueError:
            formatted_time.append(time_str)
    # Set fields if None
    if fields is None: 
        fields = PRIOR_LAKE_FIELDS
    # Assign json output type
    output_type = "geojson" if return_geo else "csv"
    # === Build API Parameters ===
    params = {
        "feature_id":   site,
        "start_time":   formatted_time[0],
        "end_time":     formatted_time[1],
        "fields":       ",".join(fields),
        "output":       output_type
    }
    # === API Request ===
    response = requests.get(BASE_URL, params=params)  
    return response

def read_pl( # Read PriorLake Response
        api_response: requests.Response
        ) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Takes a Prior Lake API response and converts it to DataFrame or GeoDataFrame.

    Parameters
    ----------
        api_response : requests.Response 
            API response object.
    Returns
    -------
        pd.DataFrame | gpd.GeoDataFrame 
            DataFrame containing api data. If response is csv, returns a 
            pandas DataFrame. If response is geojson, returns a GeoDataFrame.
    """
    # === Response to JSON Object===
    api_json = api_response.json()["results"]
    # === Convert to DataFrame ===
    if api_json["csv"]: df = pd.read_csv(io.StringIO(api_json["csv"]))
    elif api_json["geojson"]: df = gpd.GeoDataFrame.from_features(api_json["geojson"]["features"])
    return df

def get_records( # Get PriorLake Data for Site(s)
        sites: List[Union[int, str]] = None, 
        time_range: Tuple[str, str] = None,
        fields: Optional[List[str]] = None, 
        return_geo: bool = False, 
        max_workers: int = 10, 
        request_delay: float = 0.15
        ) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Get data from Hydrocron and return as a pandas DataFrame or GeoDataFrame.

    .. note::
        'sites' and 'time_range' are required parameters.\n
        'time_range' can accept both 'YYYY-MM-DD' and ISO 8601 (UTC) format (see parameters for example). Other formats could result in bugs\n        
        'fields' will be filled with all available fields [as of 9/30/25] if None.\n
        If you are querying 1 field it NEEDS to be in a list, e.g. fields=['quality_f'].\n
        If your are querying 1 site it NEEDS to be in a list, e.g. sites=['7420077552'].\n

    Parameters
    ----------
    sites : list of strings, list of ints, string, or int, required
        Site ID(s) to fetch data for. (known as lake_id in PLD)
        Ex: ['12345'] or [12345] or ['12345', '67890', ...] or [12345, 67890, ...]
    time_range : tuple of strings, required
        Start and end time in 'YYYY-MM-DD' or ISO 8601 (UTC) format. 
        Ex: ('2023-12-22', '2024-08-17') or ('2023-12-22T22:45:23Z', '2024-08-17T11:30:00Z')
    fields : list of strings or None, optional, default None
        Fields to query within the service. If None, defaults to all fields for the
        service. Ex: ['time', 'wse', 'area_total'] or ['geometry'] or None
    return_geo : bool, optional, default False
        If True, returns json:geojson request. Otherwise, returns json:csv request.
    max_workers : int, optional, default 10
        Maximum number of concurrent workers for fetching data.
    request_delay : float, optional, default 0.15
        Seconds to wait between requests (to avoid overloading the server).

    Returns
    -------
    df : pd.DataFrame or gpd.GeoDataFrame
        DataFrame(s) containing data from all requested sites.
    """
    # Setup
    def _safe_fetch(fid):
        try:
            response = call_pl(
                feature_id=fid,
                time_range=time_range,
                fields=fields,
                output_type=return_geo
            )
            if response is not None: return response
            else: print(f"Response empty from {fid}")
        except Exception as e:
            print(f"Failed for {fid}: {e}")
        return None

