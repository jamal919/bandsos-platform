#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This module provides functionalities to sort and combine already downloaded GFS forecasts into a single netCDF file. This
functionality is particularly useful when unique sagments from previous gfs forecasts are needed to be combined together
to get a continuous sflux file.

.. warning::
    This module does not provides any classes currently and the the functions in this modules are standalone.  As the 
    functionalities are not yet formalized into a data class. However, in future version this functions might be 
    depricated and marged into a data class.

'''

import warnings
import xarray as xr
import numpy as np
import pandas as pd
from glob import glob
import os
import shutil
import tempfile
import sys
import logging

def list_gfs_cycles(fdir: str, fname_pattern: str = 'gfs*.nc') -> pd.DataFrame:
    ''' 
    List available GFS forecast cycles in the `fdir` location with `fname_pattern`.
    '''
    logging.info('In list_gfs_cycles()')

    fpath = glob(os.path.join(fdir, fname_pattern))

    if len(fpath) == 0:
        warnings.warn('The list of available gfs cycles is empty!')

    cycles = pd.DataFrame({'fpath':fpath})
    cycles['fname'] = [os.path.basename(f) for f in cycles.loc[:, 'fpath']]
    cycles['cycle_id'] = [f[4:14] for f in cycles.loc[:, 'fname']] # gfs_yyyymmddhh
    cycles['start_date'] = [pd.to_datetime(f, format='%Y%m%d%H') for f in cycles.loc[:, 'cycle_id']]
    cycles = cycles.set_index('cycle_id').sort_index()
    logging.info(f'{len(cycles)} cycles found in {fdir}')
    return(cycles)

def select_gfs_cycles(
        cycles: pd.DataFrame, 
        start_date: pd.Timestamp, 
        end_date: pd.Timestamp, 
        forecast_length: pd.Timedelta = '5D',
        cycle_step: pd.Timedelta = '6H') -> pd.DataFrame:
    '''
    Selects appropriate cycles from `cycles` with `start_date` and `end_date`. 
    `forecast_length` controls how much of the forecast to be considered in the last cycle.
    `cycle_step` controls how the function search for each previous or later forecasts step by step.
    '''
    logging.info('In select_gfs_cycles()')

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    forecast_length = pd.to_timedelta(forecast_length)
    cycle_step = pd.to_timedelta(cycle_step)

    #TODO test if all necessary column in cycles exists
    start_dates = cycles.start_date.values
    end_dates = start_dates + forecast_length

    # Computing sflux start
    found_sflux_start = False
    sflux_start_date = start_date

    # Iteratively find the start date/cycle
    while not found_sflux_start:
        if sflux_start_date in start_dates:
            logging.info(f'Found {sflux_start_date} in available forecast.')
            found_sflux_start = True
        else:
            logging.info(f'Not found {sflux_start_date} in available forecast.')
            sflux_start_date = sflux_start_date - cycle_step
            logging.info(f'Will try with {sflux_start_date} in available forecast.')

        # Check if the search is above the allowed forecast_length
        if sflux_start_date - start_date > forecast_length:
            exc_msg = f'Model starts - {start_date}, Data found - {sflux_start_date} -> more than allowed forecast length {forecast_length}!'
            raise Exception(exc_msg)
        
        # Check if search reach end of the available start dates
        if sflux_start_date < start_dates[0]:
            exc_msg = f'Model starts - {start_date}, Data starts - {start_dates[0]} -> not enough data!'
            raise Exception(exc_msg)

    # Iteratively find the end date and compute the corresponding cycle from there
    found_sflux_end = False
    sflux_end_date = end_date

    while not found_sflux_end:
        if sflux_end_date in end_dates:
            found_sflux_end = True
        else:
            sflux_end_date = sflux_end_date + cycle_step
    
        # Check if the search is above the allowed forecast_length
        if sflux_end_date - end_date > forecast_length:
            exc_msg = f'Model ends - {end_date}, Data ends - {sflux_end_date} -> more than allowed forecast length {forecast_length}!'
            raise Exception(exc_msg)

        # Check if search reach end of the available end dates
        if sflux_end_date > end_dates[-1]:
            exc_msg = f'Model ends - {end_date}, Data ends - {end_dates[-1]} -> not enough data!'
            raise Exception(exc_msg)

    # Finally select the data from cycles
    is_selected = np.logical_and(end_dates <= sflux_end_date, start_dates >= sflux_start_date)
    selected_cycles = cycles.loc[is_selected, :].copy()
    
    logging.info(f'Model: {start_date} -> {end_date}')
    logging.info(f'GFS data: {sflux_start_date} -> {sflux_end_date}')

    return(selected_cycles)

def _combine_gfs_cycles_temp(cycles: pd.DataFrame, fname: str, temp_dir: str, temp_name:str):
    logging.info(f'Started preparing {len(cycles.index)-1} previous gfs cycles.')
    for i in range(len(cycles.index)-1):
        with xr.open_dataset(cycles.fpath[i]) as ds:
            dt = pd.to_timedelta(ds.time.diff(dim='time'))[0]
            start_time = cycles.start_date[i]
            end_time = cycles.start_date[i+1] - dt # to avoid overlapping with the next
            ds.sel(time=slice(start_time, end_time)).to_netcdf(os.path.join(temp_dir, f'{temp_name}_{i:02d}.nc'))
    logging.info(f'Done preparing previous cycles!')

    # The last forecast
    logging.info(f'Started preparing last cycle.')
    with xr.open_dataset(cycles.fpath[-1]) as ds:
        ds.to_netcdf(
            os.path.join(temp_dir, f'{temp_name}_{len(cycles.index):02d}.nc'), 
            encoding={'time':{'units':'days since 1900-01-01'}}
            )
    logging.info(f'Done preparing last cycle')

    # Saving to a single file
    logging.info(f'Starts merging into {temp_name}_merged.nc')
    with xr.open_mfdataset(os.path.join(temp_dir, f'{temp_name}_*.nc')) as ds:
        ds.to_netcdf(
            os.path.join(temp_dir, f'{temp_name}_merged.nc'), 
            encoding={'time':{'units':'days since 1900-01-01'}}
        )
    logging.info(f'Done merging into {temp_name}_merged.nc')

    # Interpolate and fill na
    logging.info(f'Starts filling na with linear interpolation and saving to {fname}')
    with xr.open_dataset(os.path.join(temp_dir, f'{temp_name}_merged.nc')) as ds:
        ds.interpolate_na(
            dim='time'
            ).to_netcdf(
                fname,
                encoding={'time':{'units':'days since 1900-01-01'}}
            )
    print(f'Done filling na with linear interpolation and saving to {fname}')

def combine_gfs_cycles(cycles: pd.DataFrame, fname: str):
    '''
    Combining gfs dataset from a list of `cycles`, and save to `fname`.

    Cycles - should have index(cycle name), fpath, start_date

    This method generates temporary files in system temporary folder and cleans them up upon completion or failure.
    '''
    logging.info('In combine_gfs_cycles()')
    temp_name = 'comgfs'
    
    temp_dir = './tempdir_gfs'
    try:
        os.mkdir(temp_dir)
    except FileExistsError:
        pass

    try:
        _combine_gfs_cycles_temp(cycles=cycles, fname=fname, temp_dir=temp_dir, temp_name=temp_name)
    except Exception as e:
        raise e
    finally:
        shutil.rmtree(temp_dir)

def create_gfs_data(
        start_date: pd.Timestamp, 
        end_date: pd.Timestamp, 
        forecast_length: pd.Timedelta, 
        cycle_step: pd.Timedelta, 
        fdir: str, 
        fname_pattern: str, 
        fname_out: str) -> None:

    '''
    Create gfs data to cover from `start_date` to `end_date`, with allowed `forecast_length` for each cycles found in 
    `fdir` with filenames matching `fname_pattern` and save it to `fname_out`. `cycle_step` controls how the algorithm
    search for next/previous cycle if exact cycle is not found.
    '''
    cycle_step = pd.to_timedelta(cycle_step)
    start_date = pd.to_datetime(start_date).floor(freq=cycle_step)
    end_date = pd.to_datetime(end_date).ceil(freq=cycle_step)
    logging.info(f'Preparing gfs data from {start_date} to {end_date}.')

    cycles = list_gfs_cycles(fdir=fdir, fname_pattern=fname_pattern)
    selected_cycles = select_gfs_cycles(
        cycles=cycles, 
        start_date=start_date, 
        end_date=end_date, 
        forecast_length=forecast_length, 
        cycle_step=cycle_step)
    combine_gfs_cycles(cycles=selected_cycles, fname=fname_out)


if __name__=='__main__':
    print('''
Example use: 
>>> create_gfs_data(
        start_date='2022-09-07 04:00:00', 
        end_date='2022-09-13', 
        forecast_length='5D', 
        cycle_step='6H', 
        fdir='./fluxes/gfs', 
        fname_pattern='gfs*.nc', 
        fname_out='gfs.nc'
        )
'''
    )

