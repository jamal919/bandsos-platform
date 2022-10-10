#!/usr/bin/env python

#%% imports
from bandsos.schism import Grid, Sflux, Bctides, Tidefacout
from bandsos.gfs import create_gfs_data

import xarray as xr
import pandas as pd
import numpy as np

import f90nml

import logging

import subprocess
import os
import sys
from glob import glob

#%% setup
SECONDS2DAY = 1/86400

logging.basicConfig(filename='bandsos.log', level=logging.INFO, filemode='w')

#%% functions
def init_cycle(cycle: str, model_spinup: str, forecast_length: str, cycle_step: str, cycle_format: str = '%Y%m%d%H'):
    '''
    Extracts and return a dict of `start_date`, `end_date`, `forecast_length`, `cycle_step` for a given cycle name.
    '''
    cycle_date = pd.to_datetime(cycle, format=cycle_format)
    return(
        {
            'cycle':cycle,
            'cycle_date':cycle_date,
            'start_date': cycle_date - pd.Timedelta(model_spinup),
            'end_date': cycle_date + pd.Timedelta(forecast_length),
            'forecast_length': forecast_length,
            'cycle_step': cycle_step
        }
    )

def create_gfs_sflux(fname, n_buffer_steps=2, outpath='./', step='1H', nstep=24, basedate='1970-01-01'):
    ds = xr.open_dataset(fname)
    step = pd.to_timedelta(step)
    basedate = pd.to_datetime(basedate)
    start_time = pd.to_datetime(ds.time)[0]
    end_time = pd.to_datetime(ds.time)[-1]
    x = ds['lon'].values
    y = ds['lat'].values

    sflux = Sflux(
        grid=Grid(x=x, y=y), 
        basedate=basedate, 
        sflux_type='air', 
        nstep=nstep, 
        path=os.path.join(outpath, 'sflux')
    )

    timesteps = pd.date_range(start=start_time, end=end_time, freq=step)
    
    for timestep in timesteps:
        logging.info(f'Processing - {timestep}')

        flux = {
                'uwind':ds['u10'].interp(time=timestep, lon=x, lat=y),
                'vwind':ds['v10'].interp(time=timestep, lon=x, lat=y),
                'prmsl':ds['prmsl'].interp(time=timestep, lon=x, lat=y),
                'stmp':ds['stmp'].interp(time=timestep, lon=x, lat=y),
                'spfh':ds['spfh'].interp(time=timestep, lon=x, lat=y)
            }

        sflux.write(
            at=timestep,
            flux=flux
        )

    ds.close()

    # Buffer steps
    for i in range(n_buffer_steps):
        sflux.write(
            at=timestep+step*(i+1),
            flux=flux
        )

    sflux.finish()
    sflux.sfluxtxt(dt=step)

def create_tidefacinput(start_date, end_date, savedir='./'):
    model_start = start_date
    model_end = end_date
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
    cycles = ['2022090900', '2022090906', '2022090912', '2022090918']
    cycles = ['2022090900', '2022090906']
    print(sys.argv)
    
    forecast_config = {
        'model_spinup':'2D',
        'forecast_length':'5D',
        'cycle_step':'6H',
        'cycle_format':'%Y%m%d%H'
    }

    for cycle in cycles:
        cycle_config = init_cycle(cycle=cycle, **forecast_config)

        cycledir = os.path.join('forecasts', cycle_config['cycle'])
        
        print(cycle_config['cycle'], ' -> ', cycledir)
        
        if not os.path.exists(cycledir):
            os.mkdir(cycledir)

        wave = True
        
        fname_gfs = os.path.join(cycledir, 'gfs.nc')
        create_gfs_data(
            start_date=cycle_config['start_date'], 
            end_date=cycle_config['end_date'], 
            forecast_length=cycle_config['forecast_length'], 
            cycle_step=cycle_config['cycle_step'], 
            fdir='./fluxes/gfs', 
            fname_pattern='gfs*.nc', 
            fname_out=fname_gfs)
        create_gfs_sflux(
            fname=fname_gfs, 
            n_buffer_steps=2, 
            outpath=cycledir, 
            step='1H', 
            nstep=24, 
            basedate='1970-01-01')
        create_tidefacinput(
            start_date=cycle_config['start_date'], 
            end_date=cycle_config['end_date'], 
            savedir='./')
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
