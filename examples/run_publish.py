#!/usr/bin/env python
'''
A forecasting script using bandsos platform for Bengal delta region. The script illustrates various functionalities
available in the bandsos toolbox. This program is particularly developed to be deployed using the jamal919/bandsos 
docker environment. You will need the environment variables listed in run.env file.
'''
__version__ = '0.1'

from bandsos.schism import Grid, Sflux, Bctides, Tidefacout
from bandsos.webdata import GFS_0p25_1hr
from bandsos.webdir import GithubDirectory
from bandsos.gfs import create_gfs_data
from bandsos.color import Colormap
from bandsos.post import create_water_level_tiles, create_water_level_stations

import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1 import make_axes_locatable

import cmocean.cm as ccm

import shutil
import f90nml
import logging

import subprocess
import os
import time
import json

SECONDS2DAY = 1/86400

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
    subprocess.call([tidefac], cwd=cycledir)
    bctides = Bctides()
    bctides.read(bctides_template)
    tidefac = Tidefacout()
    tidefac.read(os.path.join(cycledir, tidefac_out))
    bctides.update(tidefac=tidefac)
    bctides.updatesa(tidefac=tidefac)
    bctides.write(os.path.join(cycledir, bctides_outfile))

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

def model_generate(cycle, fdir_paths, forecast_config, executables):
    cycle_config = init_cycle(cycle=cycle, **forecast_config)
    cycle_dir = GithubDirectory(
        fdir=os.path.join(fdir_paths['forecasts_dir'], cycle_config['cycle']), 
        username=os.environ['GH_USER'], 
        access_token=os.environ['GH_TOKEN'], 
        license='mit')
    
    # GFS data creation
    fname_gfs = os.path.join(cycle_dir.fdir, 'gfs.nc')
    create_gfs_data(
        start_date=cycle_config['start_date'], 
        end_date=cycle_config['end_date'], 
        forecast_length=cycle_config['forecast_length'], 
        cycle_step=cycle_config['cycle_step'], 
        fdir=fdir_paths['gfs_dir'], 
        fname_pattern='gfs*.nc', 
        fname_out=fname_gfs)
    create_gfs_sflux(
        fname=fname_gfs, 
        n_buffer_steps=2,
        outpath=cycle_dir.fdir, 
        step='1H', 
        nstep=24, 
        basedate='1970-01-01')
    
    # Model
    create_tidefacinput(
        start_date=cycle_config['start_date'], 
        end_date=cycle_config['end_date'], 
        savedir=cycle_dir.fdir)
    update_bctides(
        tidefac=executables['tidefac_exe'], 
        bctides_template=os.path.join(fdir_paths['config_dir'], 'bctides.in.3.template'), 
        cycledir=cycle_dir.fdir)
    create_climatic_discharge(
        discharge=os.path.join(fdir_paths['discharge_dir'], 'climatic_discharge.csv'), 
        tidefacinput=os.path.join(cycle_dir.fdir, 'tidefacinput'), 
        bnds=['Karnaphuli', 'Hooghly', 'Ganges', 'Brahmaputra'], 
        outdir=cycle_dir.fdir) # Meghna is flather
    create_param(
        tidefacinput=os.path.join(cycle_dir.fdir, 'tidefacinput'), 
        param_template_file=os.path.join(fdir_paths['config_dir'], 'param.nml.template'), 
        param_output_file=os.path.join(cycle_dir.fdir, 'param.nml'),
        wave=True)
    create_wwminput(
        param_nml_file=os.path.join(cycle_dir.fdir, 'param.nml'),
        wwminput_template_file=os.path.join(fdir_paths['config_dir'], 'wwminput.nml.nobnd.template'),
        wwminput_output_file=os.path.join(cycle_dir.fdir, 'wwminput.nml')
    )
    subprocess.call(['cp', '-v', os.path.join(fdir_paths['config_dir'], 'hgrid.gr3.3.template'), os.path.join(cycle_dir.fdir, 'hgrid.gr3')])
    subprocess.call(['cp', '-v', os.path.join(cycle_dir.fdir, 'hgrid.gr3'), os.path.join(cycle_dir.fdir, 'hgrid.ll')])
    subprocess.call(['cp', '-v', os.path.join(cycle_dir.fdir, 'hgrid.gr3'), os.path.join(cycle_dir.fdir, 'hgrid_WWM.gr3')])
    subprocess.call(['cp', '-v', os.path.join(fdir_paths['config_dir'], 'vgrid.in.2D.template'), os.path.join(cycle_dir.fdir, 'vgrid.in')])
    subprocess.call(['cp', '-v', os.path.join(fdir_paths['config_dir'], 'manning.gr3.3.template'), os.path.join(cycle_dir.fdir, 'manning.gr3')])
    subprocess.call(['cp', '-v', os.path.join(fdir_paths['config_dir'], 'windrot_geo2proj.gr3.template'), os.path.join(cycle_dir.fdir, 'windrot_geo2proj.gr3')])
    subprocess.call(['cp', '-v', os.path.join(fdir_paths['config_dir'], 'station.in.3.template'), os.path.join(cycle_dir.fdir, 'station.in')])
    subprocess.call(['cp', '-v', os.path.join(fdir_paths['config_dir'], 'wwmbnd.gr3.inactive'), os.path.join(cycle_dir.fdir, 'wwmbnd.gr3')])

    if not os.path.exists(os.path.join(cycle_dir.fdir, 'outputs')):
        os.mkdir(os.path.join(cycle_dir.fdir, 'outputs'))


if __name__=='__main__':
    # Cycle
    import sys
    if len(sys.argv) < 2:
        print('Atleast one cycle needed in - run_publish.py cycle1 [cycle2 ...]')
        sys.exit(1)
    else:
        cycles = sys.argv[1:]

    # Root directory
    root_dir = '/mnt'
    
    # log file
    # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logging.basicConfig(
        filename=os.path.join(root_dir, f'run_publish_{pd.to_datetime("now").strftime("%Y%m%d%H%M%S")}.log'),
        level=logging.DEBUG, 
        filemode='w', 
        format='%(asctime)s - %(levelname)s - %(message)s')

    # Check environment variables GH_USER, GH_TOKEN, PRODUCER, EMAIL
    required_envs = ['GH_USER', 'GH_TOKEN', 'PRODUCER', 'EMAIL']
    
    for env in required_envs:
        try:
            assert env in os.environ
            logging.info(f'{env} is found in system environment')
        except Exception as e:
            raise Exception(e, f'{env} is not found inthe system environment. Have you passed .env file to docker?')

    # Git setups
    subprocess.check_call(['git', 'config', '--global', 'init.defaultBranch', 'main'])
    subprocess.check_call(['git', 'config', '--global', '--add', 'safe.directory', '*'])

    # Directory setup
    fdir_paths = {
        'config_dir':os.path.join(root_dir, 'config'),
        'fluxes_dir':os.path.join(root_dir, 'fluxes'),
        'gfs_dir':os.path.join(root_dir, 'fluxes', 'gfs'),
        'hwrf_dir':os.path.join(root_dir, 'fluxes', 'hwrf'),
        'jtwc_dir':os.path.join(root_dir, 'fluxes', 'jtwc'),
        'discharge_dir':os.path.join(root_dir, 'fluxes', 'discharge'),
        'forecasts_dir':os.path.join(root_dir, 'forecasts'),
        'log_dir':os.path.join(root_dir, 'logs'),
        'status_dir':os.path.join(root_dir, 'status')
    }
    
    forecast_config = {
        'model_spinup':'2D',
        'forecast_length':'5D',
        'cycle_step':'6H',
        'cycle_format':'%Y%m%d%H'
    }

    # Programs
    executables = {
        'tidefac_exe':shutil.which('tidefac'),
        'schism_WWM_exe':shutil.which('pschism_WWM_TVD-VL')
    }

    # Initiating status file
    status_dir = GithubDirectory(
        fdir=fdir_paths['status_dir'], 
        username=os.environ['GH_USER'], 
        access_token=os.environ['GH_TOKEN']
        )
    status_file = os.path.join(status_dir.fdir, 'status.json')
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            status = json.load(f)
    else:
        status = {
            'cycle':'cycle',
            'producer':os.environ['PRODUCER'],
            'status':'published',
            'lastupdate':pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S'),
            'lastforecast':{
                'date':'2020-05-17',
                'cycle':'00'
            }
        }
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=4, separators=(', ', ': '))
        
        status_dir.add(fpaths=[status_file], message=f':tada: Creates status repository')
    
    # Forecast loop
    for cycle in cycles:
        # Check if last forecast is already done by checking if there is manifest file in the forecast directory
        cycle_dir = GithubDirectory(
            fdir=os.path.join(fdir_paths['forecasts_dir'], cycle), 
            username=os.environ['GH_USER'], 
            access_token=os.environ['GH_TOKEN'], 
            license='mit')
        
        # Check if the cycle status needs to be updated in the status directory
        needs_status_update = False
        if int(status['cycle']) < int(cycle):
            needs_status_update = True

        # Check if the results (in out2d_1.nc) is created properly
        logging.info(f'Checking if output is geneared for {cycle}')
        out_nc = os.path.join(cycle_dir.fdir, 'outputs', 'out2d_1.nc')
        if os.path.exists(out_nc):
            logging.info(f'Output file is found.')
        else:
            raise Exception('out2d_1.nc not found')

        # Post-processing and result upload
        ## Processing the tiles
        logging.info(f'Creating output tiles for {cycle}.')
        values=np.arange(-5, 5.1, 0.01) # the range of values we want for colorbar
        colormap = Colormap(values=values, cmap=ccm.balance, midpoint=0)
        tiles_extent = [86, 93, 20.5, 24]
        tiles_resolution = 0.0025 # 250m
        colorbar_ticks = np.arange(-5, 5.1, 1)
        
        output_forecast_dir = os.path.join(cycle_dir.fdir, 'forecasts')
        if not os.path.exists(output_forecast_dir):
            os.mkdir(os.path.join(cycle_dir.fdir, 'forecasts'))
        if not os.path.exists(os.path.join(os.path.join(cycle_dir.fdir, 'forecasts', 'elev'))):
            os.mkdir(os.path.join(cycle_dir.fdir, 'forecasts', 'elev'))
        out_tiles = os.path.join(cycle_dir.fdir, 'forecasts', 'elev', 'tiles')
        if not os.path.exists(out_tiles):
            os.mkdir(out_tiles)
        tiles = create_water_level_tiles(
            out_nc=out_nc, 
            outdir=out_tiles, 
            colormap=colormap, 
            extent=tiles_extent,
            resolution=tiles_resolution)
        logging.info(f'Output tiles are generated for {cycle}.')
        
        ## Creating colorbar
        logging.info(f'Generating colorbar for output tiles for {cycle}.')
        fig, ax = plt.subplots(figsize=(0.5, 2.5), facecolor=None)
        norm = mcolors.TwoSlopeNorm(vmin=np.min(values), vcenter=0., vmax=np.max(values))
        sc = ax.scatter(np.random.randn(len(values)), np.random.randn(len(values)), c=values, cmap=ccm.balance, norm=norm)
        divider = make_axes_locatable(ax)
        cax = divider.append_axes(position='right', size='50%')
        plt.colorbar(sc, cax=cax, orientation='vertical', extend='both')
        cax.set_yticks(colorbar_ticks)
        ax.set_visible(False)
        plt.savefig(os.path.join(out_tiles, 'colorbar.png'), dpi=150, bbox_inches='tight')
        plt.close()
        logging.info(f'Colorbar is generated for {cycle}')

        ## Creating stations
        logging.info(f'Creating station output for {cycle}')
        out_station = os.path.join(cycle_dir.fdir, 'forecasts', 'elev', 'stations')
        if not os.path.exists(out_station):
            os.mkdir(out_station)
        stations = create_water_level_stations(
            out_nc=out_nc, 
            outdir=out_station, 
            station_in=os.path.join(cycle_dir.fdir, 'station.in')
            )
        logging.info(f'Station output is created for {cycle}')

        ## Creating manifest
        logging.info(f'Starting manifest creation for {cycle}')
        manifest = {
            "cycle":cycle,
            "date":pd.to_datetime(cycle, format="%Y%m%d%H").strftime('%Y-%m-%d %H:%M:%S'),
            "lastupdate":pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S'),
            "producer":os.environ['PRODUCER'],
            "version":__version__,
            "forecasts": {
                "elev": {
                    "name":"Water level",
                    "src":"forecasts/elev",
                    "layers": [
                        {
                            "name":"Map",
                            "type":"tiles",
                            "timeseries":True,
                            "colorbar":True,
                            "colorbar_file":"colorbar.png",
                            "colorscale":None,
                            "timestamps":tiles
                        },
                        {
                            "name":"Water level",
                            "type":"stations",
                            "stations":stations
                        }
                    ]
                }
            }
        }

        output_manifest_file = os.path.join(cycle_dir.fdir, 'manifest.json')
        with open(output_manifest_file, 'w') as f:
            json.dump(manifest, f, indent=4, separators=(', ', ': '))

        logging.info(f'Manifest is created for {cycle}.')

        # Uploading the forecast
        logging.info(f'Publishing the results for {cycle}.')
        cycle_dir.add(
                fpaths=[output_forecast_dir, output_manifest_file], 
                message=f':rocket: Forecast published for {cycle}'
            )
        if needs_status_update:
            status.update(
                {
                    'cycle':cycle,
                    'producer':os.environ['PRODUCER'],
                    'status':'published',
                    'lastforecast':{
                        'date':pd.to_datetime(cycle, format="%Y%m%d%H").strftime('%Y-%m-%d'),
                        'cycle':pd.to_datetime(cycle, format="%Y%m%d%H").strftime('%H')
                    },
                    'lastupdate':pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')
                }
            )
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=4, separators=(', ', ': '))
        
            status_dir.add(fpaths=[status_file], message=f':rocket: Forecast published for {cycle}')
