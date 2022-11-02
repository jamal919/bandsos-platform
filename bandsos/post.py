#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xarray as xr
import rioxarray as rio
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import matplotlib.tri as mtri
import subprocess
import json
import os
import shutil

def create_water_level_tiles(out_nc, outdir, colormap, extent=[86, 93, 20.5, 24], resolution=0.0025, drop_n_times=0):
    ds = xr.open_dataset(out_nc)
    colormap.to_colorfile(os.path.join(outdir, 'colorfile'))

    nodex = ds['SCHISM_hgrid_node_x']
    nodey = ds['SCHISM_hgrid_node_y']
    elems = ds['SCHISM_hgrid_face_nodes'][:, 0:3] - 1 # 0-based indexing
    depth = ds['depth']

    x = np.arange(extent[0], extent[1], resolution)
    y = np.arange(extent[3], extent[2], -1*resolution) # image needs to be starting top-bottom
    X, Y = np.meshgrid(x, y)

    triang = mtri.Triangulation(nodex, nodey, elems)
    depth_interpolator = mtri.LinearTriInterpolator(triang, depth)
    depth_interpolated = depth_interpolator(X, Y)
    ds_dates = pd.to_datetime(ds['time'])[drop_n_times:]
    selected_dates = ds_dates[ds_dates.hour % 3 == 0]

    for dd in selected_dates:
        dname = pd.to_datetime(dd).strftime('%Y%m%d%H')
        
        ds_day = ds['elevation'].sel(time=dd)
        interpolator = mtri.LinearTriInterpolator(triang, ds_day)
        Z = interpolator(X, Y)
        Z = (Z+depth_interpolated)*(depth_interpolated<=0)+(Z)*(depth_interpolated>0)
        Z[np.logical_and(Z<=0, depth_interpolated<=0)] = np.nan

        ds_out = xr.Dataset(
            data_vars={'elevation':(['lat', 'lon'], Z)}, 
            coords={'lon':('lon', x), 'lat':('lat', y)}
        )

        ds_out['elevation'].rio.write_nodata(np.nan, inplace=True)
        ds_out.rio.write_crs('epsg:4326', inplace=True)
        ds_out.rio.set_spatial_dims(x_dim='lon', y_dim='lat').rio.to_raster(os.path.join(outdir, f'{dname}.tif'))

        # check=True for CheckProcessError if fail
        subprocess.run(['gdaldem', 'color-relief', f'{dname}.tif', 'colorfile', '-alpha', f'{dname}_color.tif'], cwd=outdir)
        subprocess.run(['gdal2tiles.py', '-z', '6-10', '-w', 'none', f'{dname}_color.tif', f'{dname}'], cwd=outdir)
        os.remove(os.path.join(outdir, f'{dname}.tif'))
        os.remove(os.path.join(outdir, f'{dname}_color.tif'))

    fnames = [pd.to_datetime(dd).strftime('%Y%m%d%H') for dd in selected_dates]
    return([
            {
                'time':time.strftime('%Y-%m-%d %H:%M:%S'), 
                'folder':fname
            } for time, fname in zip(selected_dates, fnames) 
            ])

# Station ouputs
def create_water_level_stations(out_nc, outdir, station_in, drop_n_times=0):
    ds_orig = xr.open_dataset(out_nc)
    selected_times = pd.to_datetime(ds_orig['time'])[drop_n_times:]
    ds = ds_orig.sel(time=selected_times)

    nodex = ds['SCHISM_hgrid_node_x']
    nodey = ds['SCHISM_hgrid_node_y']

    stations = pd.read_csv(
        station_in,
        skiprows=2, 
        delim_whitespace=True, 
        header=None, 
        names=['ID', 'Lon', 'Lat', 'Depth', 'Name']
        ).drop(columns=['Depth'])

    stations['Organization'] = stations['Name'].apply(lambda x: x.split('_')[1] if len(x.split('_'))==2 else '')
    stations['Name'] = stations['Name'].apply(lambda x: x.split('_')[0]) # Keeping only the name
    stations['ID'] = stations['ID'].apply(lambda x: f'WL{x:03d}')

    xy = np.vstack([nodex, nodey]).T
    kdtree = cKDTree(xy)

    stations['dists'], stations['nodeids'] = kdtree.query(np.vstack([stations.Lon, stations.Lat]).T)

    for stationid, station in stations.iterrows():
        ds['elevation'].sel(
            nSCHISM_hgrid_node=station.nodeids
        ).to_dataframe(
        ).rename_axis(
            'Datetime'
        ).rename(
            columns={'elevation':'Water Level (m)'}
        ).loc[:, 'Water Level (m)'].to_csv(os.path.join(outdir, f'{station.ID}.csv'), index=True)

    return([station.to_dict() for _, station in stations.drop(columns=['dists', 'nodeids']).iterrows()])
