#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
import xarray as xr
import numpy as np
import pandas as pd
from glob import glob
import os
import requests
import re

class GFS_0p25_1hr:
    def __init__(self, data_dir='./gfs', data_prefix='gfs_', url='http://nomads.ncep.noaa.gov:80/dods/gfs_0p25_1hr'):
        '''
        Checking and downloading new data from web for gfs dataset.
        '''
        self.url = url
        self.data_dir = data_dir
        self.data_prefix = data_prefix
        self.available = {}
        self.downloaded = {}
        self.remaining = {}

        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)

    def check(self, min_file_size=1000000):
        '''
        Check online for new cycles, and returns true if new cycle is available, false otherwise.
        '''
        self.available = self._list_available_cycles(days=self._list_available_days())
        self.downloaded = self._list_downloaded_cycles(min_file_size=min_file_size)
        self.remaining = self._list_remaining_cycles()

        if len(self.remaining) > 0:
            # new forecast available
            return True
        else:
            # no new forecast is available
            return False

    def _list_downloaded_cycles(self, min_file_size):
        '''
        List the downloaded forecast cycles locally.
        '''
        downloaded = {}
        fpaths = glob(os.path.join(self.data_dir, f'{self.data_prefix}*.nc'))
        fnames = [os.path.basename(fpath) for fpath in fpaths]
        fsizes = [os.path.getsize(fpath) for fpath in fpaths]

        for fpath, fsize in zip(fpaths, fsizes):
            fname = os.path.basename(fpath)
            cycle = fname.split(self.data_prefix)[1].split('.nc')[0] # prefixyyyymmddhh.nc
            
            if cycle in self.available:
                if fsize > 1000000:
                    downloaded[cycle] = fpath
        
        return(downloaded)

    def _list_remaining_cycles(self):
        remaining = {}
        for cycle in self.available:
            if cycle not in self.downloaded:
                remaining.update({cycle:self.available[cycle]})
        
        return(remaining)

    def _list_available_days(self):
        '''
        List available days online
        '''
        response = requests.get(self.url)
        initial = response.text.split('<hr>')[1].replace('<br>', '').replace('<b>', '').replace('</b>', '')
        day_url_list = [line.split('"')[1] for line in initial.split('\n')[1:-2]]

        available_days = {}
        for day_url in day_url_list:
            datestring = re.findall(pattern='\d{8}', string=day_url)[0] # first element
            available_days[datestring] = day_url

        return available_days

    def _list_available_cycles(self, days):
        available_cycles = {}
        for day in days:
            url = days[day]
            prefix = day

            response = requests.get(url)
            initial = response.text.split('<hr>')[1]
            initial = initial.replace('<br>', '').replace('<b>', '').replace('</b>', '')
            initial = initial.replace('\n&nbsp;', '').replace('&nbsp', '').split('\n')
            initial = initial[1:-2]
            
            eitems = 5 # items expected 
            nitems = len(initial)//eitems
            items = np.arange(nitems)

            for item in items:
                cycle = initial[eitems*item+1].split(':')[0]
                cycle_hour = cycle[-3:-1] # extracted from gfs_0p25_1hr_00z format
                available_cycles[f'{prefix}{cycle_hour}'] = {
                    'url':f'{url}/{cycle}',
                    'inittime':pd.to_datetime(initial[eitems*item+1].split('from ')[1].split(',')[0].replace('Z', ''), format='%H%d%b%Y'),
                    'dltime':pd.to_datetime(initial[eitems*item+1].split('Z')[1][5:-4].replace(', downloaded ', ''), format='%Y%b %d %H:%M')
                }
        
        return(available_cycles)

    def download(self, extent=[0, 360, -90, 90]):
        for cycle in self.remaining:
            ds = self.get_data_handle(self.remaining[cycle]['url'])
            fname = os.path.join(self.data_dir, f'{self.data_prefix}{cycle}.nc')
            self.save_data(ds=ds, fname=fname, extent=extent)

    @staticmethod
    def get_data_handle(dataurl):
        tick = pd.to_datetime('now')
        print(f'{dataurl}: ', end='', flush=True)
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
                return(ds)

    @staticmethod
    def save_data(ds, fname, extent):
        success = False
        attempt = 1

        while not success:
            try:
                print(f'{attempt}...', end='', flush=True)
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
                    ds_out.to_netcdf(fname)

                ds_out.close()
                ds.close()
            except Exception as e:
                print("The exception raised is: ", e)
                attempt += 1
            else:
                success = True
                print(f'done.', flush=True)