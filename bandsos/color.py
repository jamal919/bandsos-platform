#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolor
import matplotlib.patches as mpatch

class Colormap:
    def __init__(self, values, cmap, vmin=None, vmax=None, midpoint=None):
        self.values = values
        self.cmap = cmap
        self.vmin = vmin
        self.vmax = vmax
        self.midpoint = midpoint

    @property
    def norm(self):
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
        # as type int is important for color to work properly
        return(np.round(self.norm * 255).astype(int))

    @property
    def rgb(self):
        return(self.cmap(self.norm))

    @property
    def rgb_8bit(self):
        return(
            np.round(self.rgb*255).astype(int)
        )

    @property
    def hex(self):
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
        values = self.values
        colors = self.rgb
        isort = np.argsort(values) # large to small values
        
        fig, ax = plt.subplots()
        for i, color in enumerate(self.rgb):
            y_pos = i/len(self.rgb)
            ax.add_patch(mpatch.Rectangle((0, y_pos), 0.75, 1, color=color))
            ax.text(0.75+0.25/2, y_pos+1/9/2, f'{self.values[i]} -{self.hex[i]}', ha='center', color='black')

    def to_colorfile(self, fname, novalue=True):
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