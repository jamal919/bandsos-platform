#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from scipy.interpolate import griddata
from scipy.spatial import distance
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import MultipleLocator
from datetime import datetime, timedelta
from netCDF4 import Dataset
from copy import deepcopy
import os

class Gr3:
    def __init__(self, nodes=[], elems=[], data=[], epsg=4326):
        '''
        Gr3 data object.
        '''
        self.nodes = np.array(nodes)
        self.elems = np.array(elems)
        self.data = np.array(data)
        self.epsg = epsg

        self.nelem = len(self.elems)
        self.nnode = len(self.nodes)

    def read(self, fname):
        '''
        Calling the gr3 object to read the data directly.
        '''
        __file = fname
        with open(__file) as f:
            ds = f.readlines()

            __line = 0
            
            # Reading the gr3 name
            self.grname = ds[__line].strip()
            __line = __line + 1
            
            # Reading the number of nodes and elements
            __nelem, __nnode = np.fromstring(string=ds[__line].split('\n')[0], count=2, sep=' ')
            self.nelem = int(__nelem)
            self.nnode = int(__nnode)
            __line = __line + 1

            # Reading the nodes
            try:
                __nodes = np.genfromtxt(fname=ds[__line:__line+self.nnode])
            except:
                raise Exception('Node data error')
            else:
                __line = __line + self.nnode
                self.nodes = np.array(__nodes[:, 1:3])
                self.data = np.array(__nodes[:, 3:])

            if len(ds) >= self.nelem + self.nnode + 2:
                try:
                    # Reading the elements
                    __elems = np.genfromtxt(fname=ds[__line:__line+self.nelem], dtype=int)
                except:
                    raise Exception('Element table error')
                else:
                    __line = __line + self.nelem
                    self.elems = np.array(__elems, dtype=int)
                    self.elems = self.elems[:, 2:]
            else:
                Warning('Element table does not exist in the file.')
        
        return(self)

    @property
    def x(self):
        return(self.nodes[:, 0])

    @property
    def y(self):
        return(self.nodes[:, 1])

    def __add__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data + other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data + other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data + other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __sub__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data - other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data - other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data - other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __mul__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data * other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data * other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data * other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __truediv__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data / other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data/other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data/other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')


    def __gt__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data>other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data>other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data>other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __ge__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data>=other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data>=other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data>=other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __lt__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data<other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data<other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data<other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __le__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data<=other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data<=other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data<=other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __pow__(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data**other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Gr3(
                    nodes=self.nodes,
                    elems=self.elems,
                    data=self.data**other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert len(other) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=self.data**other
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')
            
    def logical_and(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=np.logical_and(self.data, other.data)
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')
    
    def logical_or(self, other):
        if isinstance(other, (Gr3)):
            try:
                assert np.all(other.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=np.logical_or(self.data, other.data)
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')

    def __abs__(self):
        '''
        Absolute value of the gr3 object
        '''
        return(
            Gr3(
                nodes=self.nodes,
                elems=self.elems,
                data=np.abs(self.data)
            )
        )

    def where(self, cond, other=np.nan):
        if isinstance(cond, (Gr3)):
            try:
                assert np.all(cond.nodes.shape == self.nodes.shape)
            except:
                raise ValueError('Uneuqal gr3 object')
            else:
                data = np.zeros_like(self.data)*other
                data[cond.data] = self.data[cond.data]
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=data
                    )
                )
        elif isinstance(cond, (np.array)):
            try:
                assert len(cond) == len(self.data)
            except:
                raise ValueError('Unequal data shape')
            else:
                data = np.zeros_like(self.data)*other
                data[cond] = self.data[cond]
                return(
                    Gr3(
                        nodes=self.nodes,
                        elems=self.elems,
                        data=data
                    )
                )
        else:
            raise ValueError('Not a Gr3, array, or a number!')
            
    def inside(self, bbox):
        '''
        Return a true false grid indicating if it is inside the bbox. 

        Parameters
        ----------
        bbox : np.array, list of 4
            List of 4 indicating the bounding box [West, East, South, North]

        Returns
        -------
        Gr3

        '''
        try:
            west, east, south, north = bbox
        except:
            raise ValueError('Bbox array is not an array of 4')
        
        data = np.zeros_like(self.data)
        
        xcond = np.logical_and(self.nodes[:, 0]>=west, self.nodes[:, 0]<=east)
        ycond = np.logical_and(self.nodes[:, 1]>=south, self.nodes[:, 1]<=north)
        cond = np.logical_and(xcond, ycond)
        
        data[cond] = 1
        
        return(
            Gr3(
                nodes=self.nodes,
                elems=self.elems,
                data=data
                )
            )

    def nearest(self, of):
        '''
        Return the nearest node and associated info of the point of

        of: (x, y) or an array of (x, y)
        
        returns nearest node number, distance to it
        '''
        of = np.atleast_2d(of)
        dist = distance.cdist(self.nodes, of)
        closest_dist = np.min(dist, axis=0)
        closest_ind = np.argmin(dist, axis=0)
        return closest_ind, closest_dist

    def plot(self, ax=None, clevels=None, cmap=None, colorbar=False, subplot_kw=None, gridspec_kw=None, **fig_kw):
        '''
        plot data
        '''
        if ax is None:
            _, ax = plt.subplots(nrows=1, ncols=1, subplot_kw=subplot_kw, gridspec_kw=gridspec_kw, **fig_kw)

        if clevels is None:
            clevels = np.linspace(np.min(self.data), np.max(self.data), num=10)

        if cmap is None:
            cmap = 'jet'
        try:
            tc = ax.tricontourf(
                self.nodes[:, 0],
                self.nodes[:, 1],
                self.elems - 1, # python 0-based index
                self.data.flatten(),
                levels=clevels,
                cmap=cmap
            )
        except:
            raise Exception('Check data')
        
        if colorbar:
            divider = make_axes_locatable(ax)
            cax = divider.append_axes(
                position="right", 
                size="5%", 
                pad=0.05, 
                axes_class=plt.Axes # Important if you use cartopy to create ax
            )
            plt.colorbar(tc, cax=cax)
        
        return(ax)

    def interpolate(self, at, method='linear'):
        pass

    def to_xarray(self):
        '''
        Return an xarray dataset
        '''
        pass

    def to_netcdf(self, fname):
        '''
        Save Gr3 data as netcdf file.
        '''
        pass
    
    def save(self, fname):
        '''

        Parameters
        ----------
        fname : string
            File name of the output file

        Returns
        -------
        None.

        '''
        pass

    def __repr__(self):
        '''
        String representation of Gr3 object.
        '''
        repr_string = f'''Gr3 object with {self.nnode} nodes, {self.nelem} elemenets, {self.data.shape[1]}  data columns'''
        return(repr_string)
            
class Grid:
    def __init__(self, x, y, data=None):
        '''
        Grid object to generate grid and provides function to find various
        values at grid points.

        x: number of rows
        y: number of columns
        data: must be of the length len(x)*len(y). It will be flatten to get
        i,j,n formation
        '''
        try:
            assert isinstance(x, (list, tuple, np.ndarray))
            assert isinstance(y, (list, tuple, np.ndarray))
        except:
            raise TypeError(f'x, y must be python or numpy array')
        else:
            self.x = x
            self.y = y
            self.size = (len(self.x), len(self.y))

        # Data
        if data is None:
            self.depth = 1
            self.data = np.zeros(shape=(self.size[0], self.size[1], self.depth))
        elif isinstance(data, (np.ndarray)):
            self.depth = np.int(len(data.flatten())/self.size[0]/self.size[1])
            try:
                self.data = np.array(data).reshape((self.size[0], self.size[1], self.depth))
            except:
                raise Exception('Size mismatch')

    @property
    def meshgrid(self):
        X, Y = np.meshgrid(self.x, self.y, indexing='ij')
        return(X, Y)

    def reshape(self):
        '''
        Reshape the data to conform data structure.
        '''
        self.depth = np.int(len(self.data.flatten())/self.size[0]/self.size[1])
        self.data = self.data.reshape((self.size[0], self.size[1], self.depth))

    def __add__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data+other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data+other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data + other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i] + other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __sub__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data - other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data - other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data - other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i] - other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __mul__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data*other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data*other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data * other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i] * other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __truediv__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data/other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data/other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data/other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i]/other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __lt__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data<other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data<other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data<other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i]<other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __le__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data<=other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data<=other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data<=other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i]<=other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __gt__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data>other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data>other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data > other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i] > other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __ge__(self, other):
        if isinstance(other, (Grid)):
            try:
                assert np.all(other.size == self.size)
                assert other.depth == self.depth
            except:
                raise ValueError('Uneuqal grid object')
            else:
                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data>=other.data
                    )
                )
        elif isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data>=other
                )
            )
        elif isinstance(other, (np.ndarray)):
            try:
                assert np.all(other.shape[0:2] == self.size)
                assert len(other.shape) == 3
                assert other.shape[2] == self.depth

                return(
                    Grid(
                        x=self.x,
                        y=self.y,
                        data=self.data >= other
                    )
                )
            except:
                try:
                    assert np.all(other.shape == self.size)

                    return_data = np.copy(self.data)
                    for i in np.arange(self.depth):
                        return_data[:, :, i] = return_data[:, :, i] >= other
                    return(
                        Grid(
                            x=self.x,
                            y=self.y,
                            data=return_data
                        )
                    )
                except:
                    raise ValueError('Unequal data shape')

    def __pow__(self, other):
        if isinstance(other, (float, int)):
            return(
                Grid(
                    x=self.x,
                    y=self.y,
                    data=self.data**other
                )
            )
        else:
            raise ValueError('Only float or int as power')
    
    def __repr__(self):
        '''
        String representation.
        '''
        return(self.data.__repr__())

    def __getitem__(self, key):
        return self.data[key]

    def __getattr__(self, name):
        return getattr(self.data, name)

    def __iter__(self):
        '''
        Return a list to iterate over - i in object
        '''
        return(iter(self.data.reshape((self.size[0]*self.size[1], self.depth))))

    def apply(self, func, **kwargs):
        f = lambda x : func(x, **kwargs)

        data = np.array([f(x) for x in self])
                
        return(
            Grid(
                x=self.x,
                y=self.y,
                data=data
            )
        )

    def polar_coordinate(self, origin):
        '''
        Calculate the polar distance from a given point of interest.

        For lon,lat values, the distance is calculated using great circle distance.
        '''
        try:
            originx, originy = origin
        except:
            raise Exception('Origin must be a list of lon, lat')
        
        X, Y = self.meshgrid
        dfac = 60*1.852*1000
        dist_x = dfac*np.cos(np.deg2rad(Y))*(X-originx)
        dist_y = dfac*(Y-originy)
            
        r = np.sqrt(dist_x**2 + dist_y**2)
        theta = np.arctan2(dist_y, dist_x)

        return(
            Grid(
                x=self.x,
                y=self.y,
                data=np.array([(rr, tt) for rr, tt in zip(r.flatten(), theta.flatten())])
            )
        )

    def interpolate(self, at, depth=0, method='linear', fill_value=np.nan, rescale=False):
        '''
        Interpolate at another x,y point or grid using scipy.interpolate.griddata

        at: {list, tuple, Grid} instance
        depth: depth of grid data to interpolate
        method: {'linear', 'nearest', 'cubic'}, optional
        fill_value: value used to fill in for requested point outside of convex hull
        rescale: rescale points to unit cube before preforming interpolation

        return Grid
        '''
        X, Y = self.meshgrid

        points = np.array([(x, y) for x, y in zip(X.flatten(), Y.flatten())])
        values = self[:, :, depth].flatten()

        if isinstance(at, (list, tuple)):
            # For x, y list or tuple
            return(
                griddata(
                    points, values, 
                    at, 
                    method=method, 
                    fill_value=fill_value, 
                    rescale=rescale
                )
            )
        
        if isinstance(at, Grid):
            return(
                Grid(
                    x=at.x,
                    y=at.y,
                    data=griddata(
                        points, values, at.meshgrid,
                        method=method, 
                        fill_value=fill_value,
                        rescale=rescale
                    )
                ))

class Sflux:
    def __init__(self, grid, basedate, sflux_type='air', nstep=96, priority=1, syncstep=10, path='./sflux'):
        self.grid = grid
        self.nstep = nstep # No of step
        self.basedate = basedate
        self.sflux_type = sflux_type
        self.nfile = 0 # No file at the beginning
        self.priority = priority # sflux_air_1 or 2
        self.syncstep = syncstep # Sync the netCDF each syncstep
        self.path = path

        sflux_func_map = {
            'air' : {
                'create_netcdf' : self.create_netcdf_air,
                'put_value' : self.put_value_air
            },
            'prc' : {
                'create_netcdf' : self.create_netcdf_prc,
                'put_value' : self.put_value_prc
            },
            'rad' : {
                'create_netcdf' : self.create_netcdf_rad,
                'put_value' : self.put_value_rad
            }
        }

        if sflux_type in sflux_func_map:
            self.create_netcdf = sflux_func_map[sflux_type]['create_netcdf']
            self.put_value = sflux_func_map[sflux_type]['put_value']
        else:
            raise Exception(f"sflux_type {self.sflux_type} not correct, one of 'air', 'prc', and 'rad'")
        
        # Directory creation
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def create_netcdf_air(self):
        self.step = 0
        self.nfile = self.nfile + 1
        self.filename = f'sflux_air_{self.priority:1d}.{self.nfile:04d}.nc'
        self.filepath = os.path.join(self.path, self.filename)

        # Creating the file first
        self.nc = Dataset(self.filepath, 'w', format='NETCDF4_CLASSIC')

        
        # Creating the dimensions
        self.nc.createDimension(dimname='nx_grid', size=len(self.grid.x))
        self.nc.createDimension(dimname='ny_grid', size=len(self.grid.y))
        self.nc.createDimension(dimname='ntime', size=None)

        # Creating the variables
        # Time
        self.v_time = self.nc.createVariable(
            varname='time',
            datatype=np.float32,
            dimensions=('ntime')
        )
        strf_basedate = self.basedate.strftime('%Y-%m-%d %H:%M:%S')
        self.v_time.units = f'days since {strf_basedate:s}'
        self.v_time.long_name = 'Time'
        self.v_time.calendar = 'standard'
        self.v_time.base_date = self.basedate.timetuple()[0:4]

        # Longitude
        self.v_lon = self.nc.createVariable(
            varname='lon',
            datatype=np.float32,
            dimensions=('ny_grid', 'nx_grid')
        )
        self.v_lon.units = 'degrees_north'
        self.v_lon.long_name = 'Longitude'
        self.v_lon.standard_name = 'longitude'

        # Latitude
        self.v_lat = self.nc.createVariable(
            varname='lat',
            datatype=np.float32,
            dimensions=('ny_grid', 'nx_grid')
        )
        self.v_lat.units = 'degrees_east'
        self.v_lat.long_name = 'Latitude'
        self.v_lat.standard_name = 'latitude'

        # Uwind
        self.v_uwind = self.nc.createVariable(
            varname='uwind',
            datatype=np.float32,
            dimensions=('ntime', 'ny_grid', 'nx_grid')
        )
        self.v_uwind.units = 'm/s'
        self.v_uwind.long_name = 'Surface Eastward Air Velocity (10m AGL)'
        self.v_uwind.standard_name = 'eastward_wind'

        # Vwind
        self.v_vwind = self.nc.createVariable(
            varname='vwind',
            datatype=np.float32,
            dimensions=('ntime', 'ny_grid', 'nx_grid')
        )
        self.v_vwind.units = 'm/s'
        self.v_vwind.long_name = 'Surface Northward Air Velocity (10m AGL)'
        self.v_vwind.standard_name = 'northward_wind'

        # Prmsl
        self.v_prmsl = self.nc.createVariable(
            varname='prmsl',
            datatype=np.float32,
            dimensions=('ntime', 'ny_grid', 'nx_grid')
        )
        self.v_prmsl.units = 'Pa'
        self.v_prmsl.long_name = 'Pressure Reduced to MSL'
        self.v_prmsl.standard_name = 'air_pressure_at_mean_sea_level'

        # stmp
        self.v_stmp = self.nc.createVariable(
            varname='stmp',
            datatype=np.float32,
            dimensions=('ntime', 'ny_grid', 'nx_grid')
        )
        self.v_stmp.units = 'K'
        self.v_stmp.long_name = 'Surface Temperature (2m AGL)'
        self.v_stmp.standard_name = 'surface_temperature'

        # spfh
        self.v_spfh = self.nc.createVariable(
            varname='spfh',
            datatype=np.float32,
            dimensions=('ntime', 'ny_grid', 'nx_grid')
        )
        self.v_spfh.units = 1
        self.v_spfh.long_name = 'Specific Humidity (2m AGL)'
        self.v_spfh.standard_name = 'surface_specific_humidity'
        
        # Writing lon-lat once
        X, Y = self.grid.meshgrid
        self.v_lon[:] = X.T
        self.v_lat[:] = Y.T
        
    
    def put_value_air(self, stepi, at, flux):
        if isinstance(at, (datetime, pd.DatetimeIndex)):
            at = pd.to_datetime(at) - self.basedate
        elif isinstance(at, (timedelta, pd.Timedelta)):
            at = at
        else:
            raise Exception(f'at must be datetime or timedelta object')

        self.v_time[stepi] = at.days + at.seconds/float(86400)
        self.v_uwind[stepi, :, :] = flux['uwind']
        self.v_vwind[stepi, :, :] = flux['vwind']
        self.v_prmsl[stepi, :, :] = flux['prmsl']
        self.v_stmp[stepi, :, :] = flux['stmp']
        self.v_spfh[stepi, :, :] = flux['spfh']

        self.step = self.step + 1

        # Syncing each 10 step
        if self.step%self.syncstep:
            self.nc.sync()

    def create_netcdf_prc(self):
        raise NotImplementedError

    def put_value_prc(self):
        raise NotImplementedError

    def create_netcdf_rad(self):
        raise NotImplementedError

    def put_value_rad(self):
        raise NotImplementedError

    def close_netcdf(self):
        self.nc.close()

    def write(self, at, flux):
        # First check if self.nc is available
        if hasattr(self, 'nc'):
            if self.step < self.nstep:
                self.put_value(self.step, at, flux)
            else:
                self.close_netcdf()
                self.create_netcdf()
                self.put_value(self.step, at, flux)
        else:
            self.create_netcdf()
            self.put_value(self.step, at, flux)

    def finish(self):
        if hasattr(self, 'nc'):
            self.close_netcdf()

    def sfluxtxt(self, dt):
        dt = dt.total_seconds()
        max_window = self.nstep*dt/float(3600)
        filepath = os.path.join(self.path, 'sflux_inputs.txt')
        with open(filepath, mode='w') as f:
            f.write('&sflux_inputs\n')
            f.write('air_1_relative_weight=1.,	!air_[12]_relative_weight set the relative ratio between datasets 1 and 2\n')
            f.write('air_2_relative_weight=99., \n')
            f.write(f'air_1_max_window_hours={max_window:.1f},	!max. # of hours (offset from start time in each file) in each file of set 1\n')
            f.write('air_1_fail_if_missing=.true.,	!set 1 is mandatory\n')
            f.write('air_2_fail_if_missing=.false., 	!set 2 is optional\n')
            f.write("air_1_file='sflux_air_1', 	!file name for 1st set of 'air'\n")
            f.write("air_2_file='sflux_air_2'\n")
            f.write("uwind_name='uwind', 		!name of u-wind vel.\n")
            f.write("vwind_name='vwind', 		!name of v-wind vel.\n")
            f.write("prmsl_name='prmsl', 		!name of air pressure (@MSL) variable in .nc file\n")
            f.write("stmp_name='stmp',  		!name of surface air T\n")
            f.write("spfh_name='spfh',  		!name of specific humidity\n")
            f.write('/\n')

class Bctides:
    def __init__(self, info='', ntip=0, tip_dp=0, tip=[], nbfr=0, bfr=[], nope=0, boundaries=[]):
        self.info = deepcopy(info)
        self.nitp = deepcopy(ntip)
        self.tip_dp = deepcopy(tip_dp)
        self.tip = deepcopy(tip)
        self.nbfr = deepcopy(nbfr)
        self.bfr = deepcopy(bfr)
        self.nope = deepcopy(nope)
        self.boundaries = deepcopy(boundaries)

    def read(self, filepath):
        with open(filepath) as f:
            ds = f.readlines()
            # First the dates
            self.info = ds[0].split('\n')[0]
            __lnproc = 0

            # Then the tidal potential information
            self.ntip, self.tip_dp = np.fromstring(ds[1].split('!')[0], count=2, sep=' ')
            self.ntip = int(self.ntip)
            __lnproc = 1
            
            for i in np.arange(self.ntip):
                __talpha = ds[__lnproc+1].split('\n')[0]
                __jspc, __tamp, __tfreq, __tnf, __tear = np.fromstring(ds[__lnproc+2].split('\n')[0], count=5, sep=' ')
                __rec = dict(talpha=__talpha, jspc=__jspc, tamp=__tamp, tfreq=__tfreq, tnf=__tnf, tear=__tear)
                self.tip.append(__rec)
                __lnproc = __lnproc + 2
            
            # Reading the boundary frequencies
            self.nbfr = np.fromstring(ds[__lnproc+1], count=1, sep=' ')
            self.nbfr = int(self.nbfr)
            __lnproc = __lnproc + 1
            
            self.bfr = []
            for i in np.arange(self.nbfr):
                __alpha = ds[__lnproc+1].split('\n')[0]
                __amig, __ff, __face = np.fromstring(ds[__lnproc+2].split('\n')[0], count=3, sep=' ')
                __rec = dict(alpha=__alpha, amig=__amig, ff=__ff, face=__face)
                self.bfr.append(__rec)
                __lnproc = __lnproc + 2
            
            # Open boundary sagments
            self.nope = ds[__lnproc+1].split(' ')[0]
            self.nope = int(self.nope)
            __lnproc = __lnproc + 1

            # For each open boundary sagment
            self.boundaries = ds[__lnproc+1:len(ds)]

    def update(self, tidefac):
        # Update time
        self.info = tidefac.info
        # Updating the tidal potential nodal factor and equilibrium argument
        for __tip in self.tip:
            __talpha = __tip['talpha'].strip().upper()
            if __talpha in tidefac.const.keys():
                __tip['tnf'] = tidefac.const[__talpha][0]
                __tip['tear'] = tidefac.const[__talpha][1]

        # Updating the Boundary frequency nodal factors and equilibrium argument
        for __bfr in self.bfr:
            __alpha = __bfr['alpha'].strip().upper()
                    
            if __alpha in tidefac.const.keys():
                __bfr['ff'] = tidefac.const[__alpha][0]
                __bfr['face'] = tidefac.const[__alpha][1]

    def updatesa(self, tidefac):
        """
        The earth-equilibrium-argument represents phase of the current positon. Thus if an
        annual cycle needs to implemented in a run starting from the december, the equilibrium
        argument of the value would be omega*time
        The water level would be A*cos(omega*t + eq. arg - phase)

        Input:
            tidefac: instance of tidefac object
        """
        for __bfr in self.bfr:
            __alpha = __bfr['alpha'].strip().upper()
            if __alpha=='SA':
                sim_start = datetime(year=int(tidefac.year), month=int(tidefac.month), day=int(tidefac.day), hour=int(tidefac.hour))
                year_start = datetime(year=int(tidefac.year), month=1, day=1, hour=0)
                omega = 2*np.pi/(365*86400) # rad/sec
                delta_t = (sim_start - year_start).total_seconds() # in sec
                eq_arg = np.rad2deg(omega*delta_t) # in degrees
                __bfr['face'] = eq_arg
                

    def write(self, filepath):
        with open(filepath, 'w') as f:
            # Header information
            f.write('{:s}\n'.format(self.info))

            # Tidal potential
            f.write('{:d} {:3.2f} !ntip, tip_dp\n'.format(int(self.ntip), float(self.tip_dp)))

            for __tip in self.tip:
                f.write('{:s}\n{:d}\t{:.6f}\t{:.16f}\t{:.5f}\t{:.2f}\n'\
                        .format(__tip['talpha'].strip().upper(),\
                                int(__tip['jspc']),\
                                __tip['tamp'],\
                                __tip['tfreq'],\
                                __tip['tnf'],\
                                __tip['tear']))

            # Boundary frequencies
            f.write('{:d} !nbfr\n'.format(int(self.nbfr)))

            for __bfr in self.bfr:
                f.write('{:s}\n{:.16E}\t{:.6f}\t{:.2f}\n'\
                        .format(__bfr['alpha'].strip().upper(),\
                                __bfr['amig'],\
                                __bfr['ff'],\
                                __bfr['face']))

            # Open boundaries
            f.write('{:d} !Number of Open Boundaries\n'.format(self.nope))
            
            for __line in self.boundaries:
                f.write(__line)

class Tidefacout:
    def __init__(self, year=0, month=0, day=0, hour=0, rnday=0, const={}):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.rnday = rnday
        self.const = deepcopy(const)
    
    def read(self, filepath):
        # Reading date information
        with open(filepath, 'r') as f:
            # Reading the date section
            __ds = f.readline()
            #__date = np.array(self.r.findall(__ds), dtype='float')
            __date = np.fromstring(__ds, dtype=float, count=4, sep=',')
            self.year = __date[0]
            self.month = int(__date[1])
            self.day = int(__date[2]) 
            self.hour = int(__date[3])
            
            # Reading the run length section
            __ds = f.readline()
            __rnday = np.fromstring(__ds, dtype=float, count=1, sep=',')
            self.rnday = __rnday[0]

        # Reading the constants, node factor and eq. argument ref. to GM in deg.
        __const = np.genfromtxt(fname=filepath, dtype=None, skip_header=6, \
                                encoding=None, delimiter=None, autostrip=True)
        __const = np.array([[i for i in j] for j in __const])
        __const = {i[0].upper():[float(j) for j in i[1:3]] for i in __const}
        self.const = __const

        # Tidefac header information
        self.info = '{:.2f} days - {:4.0f}/{:02.0f}/{:02.0f} {:02.2f} UTC'.format(self.rnday,\
                self.year, self.month, self.day, self.hour)

    def __str__(self):
        return(self.info)