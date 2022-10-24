#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
The color module provides class to generate colormap, export to colorfile necessary for gdal transformation used in 
[post](post.html) module.
'''

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolor
import matplotlib.patches as mpatch

class Colormap:
    def __init__(self, values:np.ndarray, cmap:mcolor.LinearSegmentedColormap, vmin:float=None, vmax:float=None, midpoint:float=None):
        '''
        Create an instance of Colormap object for given `values`, for `cmap` colormap, with `vmin`, `vmax`, and `midpoint`.
        '''
        self.values = values
        self.cmap = cmap
        self.vmin = vmin
        self.vmax = vmax
        self.midpoint = midpoint

    @property
    def norm(self):
        '''
        Gives the normalized values for the given `values`.
        '''
        return(
            self.normalize(
                values=self.values,
                vmin=self.vmin,
                vmax=self.vmax,
                midpoint=self.midpoint
            )
        )

    @property
    def norm_8bit(self):
        '''
        Gives the 8-bit integer (0-254) values for the given `values`.
        '''
        # as type int is important for color to work properly
        return(np.round(self.norm * 255).astype(int))

    @property
    def rgb(self):
        '''
        Gives the rgba for the given `values`.
        '''
        return(self.cmap(self.norm))

    @property
    def rgb_8bit(self):
        '''
        Gives the 8-bit rgba for the given `values`.
        '''
        return(
            np.round(self.rgb*255).astype(int)
        )

    @property
    def hex(self):
        '''
        Gives the hex represetation of the colorbar for the given `values`.
        '''
        return(
            [mcolor.to_hex(color) for color in self.rgb]
        )

    def normalize(self, values, vmin=None, vmax=None, midpoint=None):
        '''
        Normalize between 0 to 255, with mid point.
        
        Output needs to be rounded and astype(int) for using with colormaps (LinearSagmentedColormaps)
        '''
        if vmin is None:
            vmin = np.min(values)
        
        if vmax is None:
            vmax = np.max(values)
        
        if midpoint is None:
            midpoint = (vmax-vmin)/2
            
        x, y = [vmin, midpoint, vmax], [0, 0.5, 1]
        norm = np.interp(values, x, y)
        return(norm)

    def plot(self):
        '''
        Returns a plot with sagmented colors, their values, and hex codes.

        .. warning::
            If the len(values) is too large, the text will overlap, and might render unreadable. This function is now
            for testing purpose.
        '''
        values = self.values
        colors = self.rgb
        isort = np.argsort(values) # large to small values
        
        fig, ax = plt.subplots()
        for i, color in enumerate(self.rgb):
            y_pos = i/len(self.rgb)
            ax.add_patch(mpatch.Rectangle((0, y_pos), 0.75, 1, color=color))
            ax.text(0.75+0.25/2, y_pos+1/9/2, f'{self.values[i]} -{self.hex[i]}', ha='center', color='black')

    def to_colorfile(self, fname, novalue=True):
        '''
        Store the color sagmentation as a gdal-complient colorfile. If `novalue` is true, a no-value line is added to
        the end of the color definition.
        '''
        values = self.values
        colors = self.rgb_8bit
        isort = np.argsort(values)[::-1] # large to small values
        
        with open(fname, 'w') as f:
            for i in isort:
                r, g, b, a = colors[i]
                f.write(f'{values[i]}\t{r}\t{g}\t{b}\t{a}\n')

            if novalue:
                r, g, b, a = 0, 0, 0, 0
                f.write(f'nv\t{r}\t{g}\t{b}\t{a}\n')

    def to_dict(self):
        '''
        Return as dictionary of rgb and hex color code, for each value in the provided values (see Colormap initialization above).
        The output of this method is particularly useful if you want to include it into a manifest file.
        '''
        values = self.values
        colors_rgb = self.rgb_8bit
        colors_hex = self.hex
        isort = np.argsort(values)[::-1] # large to small values

        color_dict = {}

        for i in isort:
            color_dict[values[i]] = {
                'rgb':colors_rgb[i],
                'hex':colors_hex[i]
            }

        return(color_dict)