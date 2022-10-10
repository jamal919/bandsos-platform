#!/usr/bin/env python
# coding: utf-8

import numpy as np
import xarray as xr
import pandas as pd
from glob import glob
import requests
import os
import warnings

# Forecast source
# For now only gfs_0p25_1hr works
# gfs_0p25 has layer information which requires further vertical interpolation
gfs_0p25_1hr = 'http://nomads.ncep.noaa.gov:80/dods/gfs_0p25_1hr'
gfs_0p25 = 'http://nomads.ncep.noaa.gov:80/dods/gfs_0p25'

# Function defs
def get_day_lists(url):
    response = requests.get(url)
    initial = response.text.split('<hr>')[1].replace('<br>', '').replace('<b>', '').replace('</b>', '')
    urls = [line.split('"')[1] for line in initial.split('\n')[1:-2]]
    return(urls)

def get_fc_list(url):
    fcname = os.path.basename(url)
    response = requests.get(url)
    initial = response.text.split('<hr>')[1]
    initial = initial.replace('<br>', '').replace('<b>', '').replace('</b>', '')
    initial = initial.replace('\n&nbsp;', '').replace('&nbsp', '').split('\n')
    initial = initial[1:-2]
    
    eitems = 5 # items expected 
    nitems = len(initial)//eitems
    items = np.arange(nitems)

    data = {
        'forecast':[fcname for item in items],
        #'ids':[int(initial[eitems*item].strip().replace(':', '')) for item in items],
        'cycle':[initial[eitems*item+1].split(':')[0] for item in items],
        'inittime':[pd.to_datetime(initial[eitems*item+1].split('from ')[1].split(',')[0].replace('Z', ''), format='%H%d%b%Y') for item in items],
        'dltime':[pd.to_datetime(initial[eitems*item+1].split('Z')[1][5:-4].replace(', downloaded ', ''), format='%Y%b %d %H:%M') for item in items],
        #'info':[initial[eitems*item+2].split('"')[1] for item in items],
        #'dds':[initial[eitems*item+3].split('"')[1] for item in items],
        #'das':[initial[eitems*item+4].split('"')[1] for item in items],
    }

    data = pd.DataFrame(data)
    data['fid'] = data.apply(lambda x: f'{x.forecast}_{x.cycle}', axis=1)
    data = data.set_index('fid')
    return(data)

def get_data(dataurl, outfname, extent=[75, 102, 5, 30]):
    print(f'{os.path.basename(dataurl)}: ', end='', flush=True)
    success = False
    attempt = 1
    while not success:
        try:
            print(f'{attempt}...', end='', flush=True)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                ds = xr.open_dataset(dataurl)
        except:
                attempt += 1
        else:
            success = True
            print(f'connected...', end='', flush=True)

    lon_select = ds['lon'].where(np.logical_and(ds.lon>=extent[0], ds.lon<=extent[1])).dropna(dim='lon')
    lat_select = ds['lat'].where(np.logical_and(ds.lat>=extent[2], ds.lat<=extent[3])).dropna(dim='lat')
    
    # To suppress warning related to 1-1-1 in time
    ds_out = xr.Dataset(
        {
            'prmsl':ds['prmslmsl'].sel(lat=lat_select, lon=lon_select),
            'u10':ds['ugrd10m'].sel(lat=lat_select, lon=lon_select),
            'v10':ds['vgrd10m'].sel(lat=lat_select, lon=lon_select),
            'stmp':ds['tmp2m'].sel(lat=lat_select, lon=lon_select),
            'spfh':ds['rh2m'].sel(lat=lat_select, lon=lon_select),
            'dlwrf':ds['dlwrfsfc'].sel(lat=lat_select, lon=lon_select),
            'dswrf':ds['dswrfsfc'].sel(lat=lat_select, lon=lon_select),
            'prate':ds['pratesfc'].sel(lat=lat_select, lon=lon_select),
        }
    )
    
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        ds_out.to_netcdf(outfname)

    print('done')

    ds_out.close()
    ds.close()
    
def gen_fnames(forecast, origin, savedir, last=False):
    if last:
        fc = forecast.iloc[-1].to_dict()
    else:
        fc = forecast

    dataurl = f"{origin}/{fc['forecast']}/{fc['cycle']}"
    outfname = f"{savedir}/{fc['forecast']}_{fc['cycle']}.nc" 
    return({'dataurl':dataurl, 'outfname':outfname})

# Downloading starts here
# GFS data
day_urls = get_day_lists(gfs_0p25_1hr)
fclist = pd.DataFrame()
for day_url in day_urls:
    fclist = fclist.append(get_fc_list(day_url))


gfsdir = './forecasts/gfs'
fnames = glob(f'{gfsdir}/*.nc')
fsizes = [os.path.getsize(fname) for fname in fnames]
fnames = [os.path.basename(fname).replace('.nc', '') for fname in fnames]

fclist_to_download = fclist.copy()
for fname, fsize in zip(fnames, fsizes):
    if fname in fclist_to_download.index:
        if fsize > 1000000:
            fclist_to_download = fclist_to_download.drop(fname)

if len(fclist_to_download) == 0:
    print(f'All GFS data downloaded!')
else:
    print(f'{len(fclist_to_download)} cycles of GFS data available. Downloading...')

    for fcid, fc in fclist_to_download.iterrows():
        try:
            get_data(**gen_fnames(fc, origin=gfs_0p25_1hr, savedir=gfsdir))
        except:
            print('Failed! We will try again later!')

    # fclist_to_download.apply(
    #     lambda x: get_data(**gen_fnames(x, origin=gfs_0p25_1hr, savedir=gfsdir)),
    #     axis=1
    # )

# HWRF forecasts
import requests
from bs4 import BeautifulSoup
r = requests.get('https://www.emc.ncep.noaa.gov/gc_wmb/vxt/HWRF/index.php')
soup = BeautifulSoup(r.text, "html.parser")

hwrf_dir = './forecasts/hwrf'
if not os.path.exists(hwrf_dir):
    os.mkdir(hwrf_dir)

forms = soup.find('td', {'name':'activeNorth Indian Ocean'}).find_all('form')

for i, form in enumerate(forms, start=1):
    details = {}
    
    action = form.attrs.get("action").lower()
    method = form.attrs.get("method", "get").lower()
    
    inputs = []
    for input_tag in form.find_all("input"):
        input_type = input_tag.attrs.get("type", "text")
        input_name = input_tag.attrs.get("name")
        input_value =input_tag.attrs.get("value", "")
        inputs.append({"type": input_type, "name": input_name, "value": input_value})
    
    details["action"] = action
    details["method"] = method
    details["inputs"] = inputs

    params = {}
    for input in details['inputs']:
        if input['type']=='hidden':
            params[input['name']]=input['value']
    print(f'Going to call tcall.php with params :')
    for item in params:
        print(f'\t{item}:{params[item]}')

    url_tcall = 'https://www.emc.ncep.noaa.gov/gc_wmb/vxt/HWRF/tcall.php'
    req_tcall = requests.post(url_tcall, data=params)
    soup_tcall = BeautifulSoup(req_tcall.text, 'html.parser')
    cycles = soup_tcall.find('select', {'name':'selectCycle'}).find_all('option')
    cycles = [cycle.text for cycle in cycles]
    print(f'{len(cycles)} HWRF forecast cycles available')


    # Saving the cycles
    stormdir = f'https://www.emc.ncep.noaa.gov/gc_wmb/vxt/HWRFForecast/RT2022_NIO/'

    for cycle in cycles:
        stormfilename = f'{cycle.lower()}.trak.hwrf.atcfunix'
        stormfile = os.path.join(hwrf_dir, stormfilename)
        if os.path.exists(stormfile):
            print(f'\t{cycle} : {stormfilename} exists!')
        else:
            hwrf_atcf_url = f'{stormdir}/{params["selectStorm"]}/{cycle}/{stormfilename}'
            req_atcf = requests.get(hwrf_atcf_url)
            req_atcf.text

            with open(stormfile, 'w') as f:
                f.writelines(req_atcf.text)

            print(f'\t{cycle} : {stormfilename} downloaded!')

    # JTWC BEST track as in NOAA website
    timenow_utc = pd.to_datetime('now')
    jtwc_dir = './forecasts/jtwc'
    if not os.path.exists(jtwc_dir):
        os.mkdir(jtwc_dir)

    import re

    if len(cycles) > 0:
        lastcycle, lasttime = cycles[0].split('.')
        rs = re.search(r"\d+", lastcycle)
        trackid = lastcycle[rs.start():rs.end()]
        lasttime = pd.to_datetime(lasttime, format='%Y%m%d%H')

        prefixes = ['a', 'b'] # a for models, b for best
        
        for prefix in prefixes:
            storm_name = f'{prefix}io{trackid}{lasttime.year}.dat'
            decks_url = 'https://www.emc.ncep.noaa.gov/gc_wmb/vxt/DECKS'
            decks_storm = f'{decks_url}/{storm_name}'
            suffix = timenow_utc.strftime('%d')
            print(f'Downloading file - {storm_name}')

            decks_req = requests.get(decks_storm)
            with open(os.path.join(jtwc_dir, f'{storm_name}.{suffix}'), 'w') as f:
                f.writelines(decks_req.text)
    else:
        print('No current storm')
