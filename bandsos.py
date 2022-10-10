#!/usr/bin/env python

#%% imports
from bandsos.schism import Grid, Sflux, Bctides, Tidefacout

import xarray as xr
import pandas as pd
import numpy as np

import f90nml

import logging

import subprocess
import os
from glob import glob

#%% setup
SECONDS2DAY = 1/86400

logging.basicConfig(filename='bandsos.log', level=logging.INFO, filemode='w')

#%% functions
def cycle2dates(cycle: str, model_spinup: str, forecast_length: str, cycle_step: str, cycle_format: str = '%Y%m%d%H'):
    cycle_date = pd.to_datetime(cycle, format=cycle_format)
    return(
        {
            'start_date': cycle_date - pd.Timedelta(model_spinup),
            'end_date': cycle_date + pd.Timedelta(forecast_length),
            'forecast_length': forecast_length,
            'cycle_step': cycle_step
        }
    )

def get_gfs_list(
        fdir, 
        cycle, 
        fname_pattern='gfs*.nc', 
        cycle_format='%Y%m%d%H', 
        cycle_step='6H', 
        n_previous_cycles=8, 
        n_buffer_cycle=1,
        gfs_length_day=5,
        raise_exception=True):

    fpath = glob(os.path.join(fdir, fname_pattern))

    cycledate = pd.to_datetime(cycle, format=cycle_format)
    model_start_date = cycledate - pd.to_timedelta(cycle_step)*n_previous_cycles
    sflux_start_date = model_start_date - pd.to_timedelta(cycle_step)*n_buffer_cycle 

    cycles = pd.DataFrame({'fpath':fpath})
    cycles['fname'] = [os.path.basename(f) for f in cycles.loc[:, 'fpath']]
    cycles['cycleid'] = [f[3:11]+f[25:27] for f in cycles.loc[:, 'fname']]
    cycles['startdate'] = [pd.to_datetime(f, format='%Y%m%d%H') for f in cycles.loc[:, 'cycleid']]
    cycles['enddate'] = cycles['startdate'] + pd.to_timedelta('1D')*gfs_length_day
    cycles = cycles.where(cycles['startdate'] <= cycledate).dropna()
    cycles = cycles.set_index('cycleid')
    selected_cycles = cycles.where(
        (cycles['enddate'] - sflux_start_date) >= pd.to_timedelta('1D')*(gfs_length_day - 2)
    ).dropna()
    
    available_sflux_start_date = selected_cycles['startdate'][0]
    available_sflux_end_date = selected_cycles['enddate'][-1]

    if raise_exception & (available_sflux_start_date > model_start_date):
        raise Exception('Not enough sflux files available for requested simulation')

    return({
        'model_start':model_start_date,
        'sflux_start':available_sflux_start_date,
        'sflux_end':available_sflux_end_date,
        'sflux_files':selected_cycles
    })


def create_gfs_sflux(gfs_list, n_buffer_steps=2, outpath='./'):
    ds = xr.open_dataset(gfs_list['sflux_files']['fpath'][0])

    sflux_params = {
        'basedate':gfs_list['sflux_start'],
        'x':ds['lon'].values,
        'y':ds['lat'].values,
        'step':ds['time'].values[1] - ds['time'].values[0],
        'nstep':len(ds['time'])
    }
    
    ds.close()

    sflux = Sflux(
        grid=Grid(x=sflux_params['x'], y=sflux_params['y']), 
        basedate=pd.to_datetime(sflux_params['basedate']), 
        sflux_type='air', 
        nstep=sflux_params['nstep'], 
        path=os.path.join(outpath, 'sflux')
    )


    for _, cycle in gfs_list['sflux_files'].iterrows():
        ds = xr.open_dataset(cycle['fpath'])
        timesteps = pd.to_datetime(ds['time'].values)

        for timestep in timesteps:
            logging.info(f'Processing - {timestep}')

            flux = {
                    'uwind':ds['u10'].sel(time=timestep, lon=sflux_params['x'], lat=sflux_params['y']),
                    'vwind':ds['v10'].sel(time=timestep, lon=sflux_params['x'], lat=sflux_params['y']),
                    'prmsl':ds['prmsl'].sel(time=timestep, lon=sflux_params['x'], lat=sflux_params['y']),
                    'stmp':ds['stmp'].sel(time=timestep, lon=sflux_params['x'], lat=sflux_params['y']),
                    'spfh':ds['spfh'].sel(time=timestep, lon=sflux_params['x'], lat=sflux_params['y'])
                }

            sflux.write(
                at=timestep,
                flux=flux
            )

        ds.close()

    # Buffer steps
    for i in range(n_buffer_steps):
        sflux.write(
            at=timestep+sflux_params['step']*(i+1),
            flux=flux
        )

    sflux.finish()
    sflux.sfluxtxt(dt=pd.Timedelta(sflux_params['step']))


def create_tidefacinput(gfs_list, savedir='./'):
    model_start = gfs_list['model_start']
    model_end = gfs_list['sflux_end']
    rnday = (model_end - model_start).total_seconds()*SECONDS2DAY
    start_year = int(model_start.strftime('%Y'))
    start_month = int(model_start.strftime('%m'))
    start_day = int(model_start.strftime('%d'))
    start_hour = int(model_start.strftime('%H'))

    with open(os.path.join(savedir, 'tidefacinput'), 'w') as f:
        f.write(f'{start_year},{start_month},{start_day},{start_hour}\n')
        f.write(f'{rnday}\n')

def update_bctides(tidefac, bctides_template, bctides_outfile='bctides.in', tidefac_out='tide_fac.out', cycledir='./'):
    subprocess.call([tidefac])
    bctides = Bctides()
    bctides.read(bctides_template)
    tidefac = Tidefacout()
    tidefac.read(tidefac_out)
    bctides.update(tidefac=tidefac)
    bctides.updatesa(tidefac=tidefac)
    bctides.write(os.path.join(cycledir, bctides_outfile))
    subprocess.call(['mv', '-v', 'tidefacinput', os.path.join(cycledir, 'tidefacinput')])
    subprocess.call(['mv', '-v', 'tide_fac.out', os.path.join(cycledir, 'tide_fac.out')])

def create_climatic_discharge(discharge, tidefacinput, bnds, outdir='./'):
    ds = pd.read_csv(discharge).set_index('Day')

    with open(tidefacinput, 'r') as f:
        tm = f.readlines()
        start_year, start_month, start_day, start_hour = np.fromstring(tm[0], dtype=int, count=4, sep=',')
        rnday = np.fromstring(tm[1], dtype=float, count=1, sep=',')
        rnday = int(np.ceil(rnday))
        fxday = rnday + 1

    starttime = pd.to_datetime(f'{start_year}-{start_month:02d}-{start_day:02d} {start_hour:02d}:00:00')
    days = pd.date_range(start=starttime, periods=fxday, freq='1D')

    flux = ds.loc[days.dayofyear, bnds] * -1 # - is inflow
    flux = flux.set_index((days-days[0]).total_seconds())
    flux.to_csv(os.path.join(outdir, 'flux.th'), sep='\t', float_format='%.1f', header=None, index=True)

def create_param(tidefacinput, param_template_file, param_output_file, wave=True):
    with open(tidefacinput, 'r') as f:
        tm = f.readlines()
        start_year, start_month, start_day, start_hour = np.fromstring(tm[0], dtype=float, count=4, sep=',')
        rnday = np.fromstring(tm[1], dtype=float, count=1, sep=',')

    patch_nml = f90nml.Namelist({
        'CORE':{
            'rnday':float(rnday)
        },
        'OPT':{
            'start_year':int(start_year),
            'start_month':int(start_month),
            'start_day':int(start_day),
            'start_hour':float(start_hour)
        }
    })

    if wave:
        patch_nml.patch(
            {
                'CORE':{
                    'msc2': 12,
                    'mdc2': 12
                },
                'OPT':{
                    'icou_elfe_wwm': 1,
                    'nstep_wwm': 6,
                    'cur_wwm':1
                }
            }
        )

    f90nml.patch(param_template_file, patch_nml, param_output_file)

def create_wwminput(param_nml_file, wwminput_template_file, wwminput_output_file):
    param_nml = f90nml.read(param_nml_file)

    rnday = float(param_nml['CORE']['rnday'])

    start_year = param_nml['OPT']['start_year']
    start_month = param_nml['OPT']['start_month']
    start_day = param_nml['OPT']['start_day']
    start_hour = float(param_nml['OPT']['start_hour'])
    start_minute = start_hour%1 * 60
    start_hour = np.floor(start_hour)
    start_second = start_minute%1 * 60
    start_minute = np.floor(start_minute)
    start_second = np.floor(start_second)
    start_time = pd.to_datetime(f'{start_year:04d}-{start_month:02d}-{start_day:02d} {start_hour:02.0f}:{start_minute:02.0f}:{start_second:02.0f}')
    end_time = start_time + pd.Timedelta(rnday, unit='D')

    patch_nml = {
        'PROC':{
            'BEGTC':start_time.strftime('%Y%m%d.%H%M%S'),
            'DELTC':param_nml['CORE']['dt']*param_nml['OPT']['nstep_wwm'],
            'UNITC':'SEC',
            'ENDTC':end_time.strftime('%Y%m%d.%H%M%S'),
            'DMIN':param_nml['OPT']['h0']
        },
        'GRID':{
            'MSC':param_nml['CORE']['msc2'],
            'MDC':param_nml['CORE']['mdc2']
        },
        'BOUC':{
            'BEGTC':start_time.strftime('%Y%m%d.%H%M%S'),
            'ENDTC':end_time.strftime('%Y%m%d.%H%M%S')
        },
        'HISTORY':{
            'BEGTC':start_time.strftime('%Y%m%d.%H%M%S'),
            'ENDTC':end_time.strftime('%Y%m%d.%H%M%S'),
            'OUTSTYLE':'NO'
        },
        'STATION':{
            'BEGTC':start_time.strftime('%Y%m%d.%H%M%S'),
            'ENDTC':end_time.strftime('%Y%m%d.%H%M%S'),
            'OUTSTYLE':'STE',
            'DEFINETC':-1
        },
        'HOTFILE':{
            'BEGTC':start_time.strftime('%Y%m%d.%H%M%S'),
            'ENDTC':end_time.strftime('%Y%m%d.%H%M%S')
        }
    }

    f90nml.patch(wwminput_template_file, patch_nml, wwminput_output_file)

def template_script(template, cycledir):
    with open(template, 'r') as f:
        ds = f.read()

    ds = ds.replace('<cycle>', os.path.basename(cycledir))

    with open(os.path.join(cycledir, os.path.basename(template)), 'w') as f:
        f.write(ds)


#%% Main section
if __name__=='__main__':
    cycles = ['2022090500', '2022090506', '2022090512', '2022090518']
    
    for cycle in cycles:
        cycledir = os.path.join('forecasts', cycle)
        print(cycle, ' -> ', cycledir)
        if not os.path.exists(cycledir):
            os.mkdir(cycledir)

        wave = True
        
        gfs_list = get_gfs_list(fdir='./fluxes/gfs', cycle=cycle)
        create_gfs_sflux(gfs_list=gfs_list, outpath=cycledir)
        create_tidefacinput(gfs_list=gfs_list, savedir='./')
        update_bctides(
            tidefac='./scripts/tidefac', 
            bctides_template='config/bctides.in.3.template', 
            cycledir=cycledir)
        create_climatic_discharge(
            discharge='./fluxes/discharge/climatic_discharge.csv', 
            tidefacinput=os.path.join(cycledir, 'tidefacinput'), 
            bnds=['Karnaphuli', 'Hooghly', 'Ganges', 'Brahmaputra'], 
            outdir=cycledir) # Meghna is flather
        create_param(
            tidefacinput=os.path.join(cycledir, 'tidefacinput'), 
            param_template_file='./config/param.nml.template', 
            param_output_file=os.path.join(cycledir, 'param.nml'),
            wave=wave)

        create_wwminput(
            param_nml_file=os.path.join(cycledir, 'param.nml'),
            wwminput_template_file='./config/wwminput.nml.nobnd.template',
            wwminput_output_file=os.path.join(cycledir, 'wwminput.nml')
        )

        subprocess.call(['cp', 'config/hgrid.gr3.3.template', os.path.join(cycledir, 'hgrid.gr3')])
        subprocess.call(['cp', os.path.join(cycledir, 'hgrid.gr3'), os.path.join(cycledir, 'hgrid.ll')])
        subprocess.call(['cp', 'config/vgrid.in.2D.template', os.path.join(cycledir, 'vgrid.in')])
        subprocess.call(['cp', 'config/manning.gr3.3.template', os.path.join(cycledir, 'manning.gr3')])
        subprocess.call(['cp', 'config/windrot_geo2proj.gr3.template', os.path.join(cycledir, 'windrot_geo2proj.gr3')])
        subprocess.call(['cp', 'config/station.in.3.template', os.path.join(cycledir, 'station.in')])
        if wave:
            subprocess.call(['cp', 'config/wwmbnd.gr3.inactive', os.path.join(cycledir, 'wwmbnd.gr3')])

        template_script(template='./scripts/run.slurm', cycledir=cycledir)
        template_script(template='./scripts/jeanzay_upload.sh', cycledir=cycledir)
        template_script(template='./scripts/jeanzay_download.sh', cycledir=cycledir)

        template_script(template='./scripts/run.pbs', cycledir=cycledir)
        template_script(template='./scripts/thor_upload.sh', cycledir=cycledir)
        template_script(template='./scripts/thor_download.sh', cycledir=cycledir)

# %%
