#!/bin/env python
# -*coding: UTF-8 -*-
#
# Provide some basic methods for plotting
# plot.cmap_robustness
# plot.latlongrid
# plot.scaler
# plot.reducer
# plot.quant
#
# Created by gmaze on 2017/12/11
__author__ = 'gmaze@ifremer.fr'

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from sklearn.utils import validation
import sklearn
import pandas as pd
import seaborn as sns
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
sns.set_context("paper")
from . import pcmodel
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

def cmap_robustess():
    """ Return a categorical colormap for robustness """
    return mpl.colors.ListedColormap(['#FF0000', '#CC00FF', '#0066FF', '#CCFF00', '#00FF66'])

def cmap_discretize(name, K):
    """Return a discrete colormap from a quantitative or continuous colormap name

        name: name of the colormap, eg 'Paired' or 'jet'
        K: number of colors in the final discrete colormap
    """
    if name in ['Set1', 'Set2', 'Set3', 'Pastel1', 'Pastel2', 'Paired', 'Dark2', 'Accent']:
        # Segmented (or quantitative) colormap:
        N_ref = {'Set1':9,'Set2':8,'Set3':12,'Pastel1':9,'Pastel2':8,'Paired':12,'Dark2':8,'Accent':8}
        N = N_ref[name]
        cmap = plt.get_cmap(name=name)
        colors_i = np.concatenate((np.linspace(0, 1., N), (0., 0., 0., 0.)), axis=0)
        cmap = cmap(colors_i) # N x 4
        n = np.arange(0, N)
        new_n = n.copy()
        if K > N:
            for k in range(N,K):
                r = np.roll(n,-k)[0][np.newaxis]
                new_n = np.concatenate((new_n, r), axis=0)
        new_cmap = cmap.copy()
        new_cmap = cmap[new_n,:]
        new_cmap = mcolors.LinearSegmentedColormap.from_list(name + "_%d" % K, colors = new_cmap, N=K)
    else:
        # Continuous colormap:
        N = K
        cmap = plt.get_cmap(name=name)
        colors_i = np.concatenate((np.linspace(0, 1., N), (0., 0., 0., 0.)))
        colors_rgba = cmap(colors_i) # N x 4
        indices = np.linspace(0, 1., N + 1)
        cdict = {}
        for ki, key in enumerate(('red', 'green', 'blue')):
            cdict[key] = [(indices[i], colors_rgba[i - 1, ki], colors_rgba[i, ki])
                          for i in np.arange(N + 1)]
        # Return colormap object.
        new_cmap = mcolors.LinearSegmentedColormap(cmap.name + "_%d" % N, cdict, N)
    return new_cmap

def colorbar_index(ncolors, cmap, **kwargs):
    """Adjust colorbar ticks with discrete colors"""
    cmap = cmap_discretize(cmap, ncolors)
    mappable = cm.ScalarMappable(cmap=cmap)
    mappable.set_array([])
    mappable.set_clim(-0.5, ncolors+0.5)
    colorbar = plt.colorbar(mappable, **kwargs)
    colorbar.set_ticks(np.linspace(0, ncolors, ncolors))
    colorbar.set_ticklabels(range(ncolors))
    return colorbar

def latlongrid(ax, dx=5., dy=5., fontsize=6, **kwargs):
    """ Add latitude/longitude grid to a cartopy geoaxes  """
    if not isinstance(ax, cartopy.mpl.geoaxes.GeoAxesSubplot):
        raise ValueError("Please provide a cartopy.mpl.geoaxes.GeoAxesSubplot instance")
    defaults = {'linewidth':.5, 'color':'gray', 'alpha':0.5, 'linestyle':'--'}
    gl=ax.gridlines(crs=ax.projection, draw_labels=True, **{**defaults, **kwargs})
    gl.xlocator = mticker.FixedLocator(np.arange(-180, 180+1, dx))
    gl.ylocator = mticker.FixedLocator(np.arange(-90, 90+1, dy))
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabels_top = False
    gl.xlabel_style = {'fontsize':fontsize}
    gl.ylabels_right = False
    gl.ylabel_style = {'fontsize':fontsize}
    return gl

# def plot(m, type=None, ax=None, subplot_kw=None, **kwargs):
#     if type == 'scaler':
#         return scaler(m, subplot_kw=subplot_kw, **kwargs)
#     elif type == 'reducer':
#         return reducer(m, subplot_kw=subplot_kw, **kwargs)
#     else:
#         print('You can plot the scaler properties using pcm.plot.scaler()')

class _PlotMethods(object):
    """
        Enables use of pyxpcm.plot functions as attributes on a PCM object.
        For example: m.plot(), m.plot.scaler(), m.plot.cmap('Set2'), m.plot.colorbar()
    """

    def __init__(self, m):
        self._pcm = m
        self._cmap = self.cmap()

    def __call__(self, **kwargs):
        raise ValueError("Please use one of the plotting methods: cmap, colorbar, subplots, scaler, reducer, timeit, preprocessed")
        # return plot(self._pcm, **kwargs)

    def cmap(self, name='Set2', palette=False):
        """Return a categorical colormap for this PCM

            Parameters
            ----------
            name : str
                Name of the colormap

            palette : bool
                If False (default), return a :class:``matplotlib.colors.LinearSegmentedColormap``
                If True, return a Seaborn color_palette

            Returns
            -------
            A colormap for classification label

        """
        if not palette:
            self._cmap = cmap_discretize(name, self._pcm.K)
        else:
            self._cmap = sns.color_palette(name, self._pcm.K)
        return self._cmap

    def colorbar(self, cmap=None, **kwargs):
        """Add a colorbar to current plot with centered ticks on discrete colors"""
        if cmap==None:
            cmap=self._cmap
        z = { **{'fraction':0.03, 'label':'Class'}, **kwargs}
        return colorbar_index(ncolors=self._pcm.K, cmap=cmap, **z)

    def scaler(self, **kwargs):
        """Plot PCM scaler properties"""
        return scaler(self._pcm, **kwargs)

    def reducer(self, **kwargs):
        """Plot PCM reducer properties"""
        return reducer(self._pcm,  **kwargs)

    def subplots(self, maxcols=3, K=np.Inf, subplot_kw=None, **kwargs):
        """ Return (figure, axis) with one subplot per cluster

            Parameters
            ----------
            maxcols : int
                Maximum number of columns to use

            **kwargs to pyplot.subplots

            Returns
            -------
            fig : :class:`matplotlib.pyplot.figure.Figure`

            ax : :class:`matplotlib.axes.Axes` object or array of Axes objects.
                *ax* can be either a single :class:`matplotlib.axes.Axes` object or an
                array of Axes objects if more than one subplot was created.  The
                dimensions of the resulting array can be controlled with the squeeze
                keyword, see above.

            Example
            -------
            fig, ax = m.plot.subplots(maxcols=4, sharey=True, figsize=(12,6))

            __author__: gmaze@ifremer.fr
        """
        nrows = 1
        if K == np.Inf:
            K = self._pcm.K
        ncols = K

        if K > maxcols:
            nrows = 1 + np.int(K / maxcols)
            ncols = maxcols
        if ncols == 1:
            nrows = K
        if not subplot_kw:
            fig, ax = plt.subplots(nrows=nrows, ncols=ncols, **kwargs)
        else:
            fig, ax = plt.subplots(nrows=nrows, ncols=ncols, subplot_kw=subplot_kw, **kwargs)

        ax = np.array(ax).flatten()
        for i in range(K, nrows * ncols):
            fig.delaxes(ax[i])
        return fig, ax

    def timeit(self, group='Method', split='Sub-method', subplot_kw=None, style='white', **kwargs):
        """ Plot registered timing of operations

            Parameters
            ----------
            Param : ParamType
                DescriptionParam

            Returns
            -------

            Example
            -------

            __author__: gmaze@ifremer.fr
        """

        # Read timings:
        df = self._pcm.timeit

        # Get max levels:
        dpt = list()
        [dpt.append(len(key.split("."))) for key in self._pcm._timeit]
        max_dpt = np.max(dpt)

        with sns.axes_style(style):
            defaults = {'figsize': (5, 3), 'dpi': 90}
            if not subplot_kw:
                fig, ax = plt.subplots(**{**defaults, **kwargs})
            else:
                fig, ax = plt.subplots(**{**defaults, **kwargs}, subplot_kw=subplot_kw)

            if max_dpt == 1: # 1 Level:
                df.plot(kind='barh', ax=ax)
                # ylabel = 'Method'

            if max_dpt == 2: # 2 Levels:
                # df = df.T
                df.plot(kind='barh', stacked=1, legend=1, subplots=0, ax=ax)
                # ylabel = 'Method'

            if max_dpt > 2:
                # Select 2 dimensions to plot:
                df = df.groupby([group, split]).sum()
                df = df.unstack(0)
                if 'total' in df.index:
                    df.drop('total', inplace=True)
                if 'total' in df.keys():
                    df.drop('total', axis=1, inplace=True)
                if '' in df.index:
                    df.drop('', inplace=True)
                df = df.T
                df = df[df.sum(axis=1)!=0]
                df.plot(kind='barh', stacked=1, legend=0, subplots=0, ax=ax)
                plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

            sns.despine()
            ax.grid(True)
            ax.set_xlabel('Time [ms]')
            ax.set_ylabel(group)
        return fig, ax, df

    def preprocessed(self, ds, features=None, dim=None, n=1000, kde=False, style='darkgrid', **kargs):
        """ Pairwise scatter plot of pre-processed features

            Parameters
            ----------
            ds: :class:`xarray.DataSet`
                The dataset to work with

            features: dict()
                Definitions of PCM features in the input :class:`xarray.DataSet`.
                If not specified or set to None, features are identified using :class:`xarray.DataArray` attributes 'feature_name'.

            n : int
                Number of samples to use in scatter plots

            Returns
            -------
            g : :class:`seaborn.axisgrid.PairGrid`
                Seaborn Pairgrid instance

            __author__: gmaze@ifremer.fr
        """

        # Get preprocessed features (the [n_samples, n_features] numpy array seen by the classifier)
        X, sampling_dims = self._pcm.preprocessing(ds, features=features, dim=dim)

        # Create a dataframe for seaborn plotting machinery:
        df = X.to_dataframe('features').unstack(0)
        df.loc['labels'] = self._pcm._classifier.predict(X)
        df = df.T

        # Seaborn PairGrid plot:
        random_rows = np.random.choice(range(X.shape[0]), np.min((n, X.shape[0])), replace=False)
        with sns.axes_style(style):
            defaults = {'height':2.5, 'aspect':1, 'hue':'labels', 'palette': self.cmap(palette=True),
                        'vars':self._pcm._xlabel, 'despine':False}
            g = sns.PairGrid(df.iloc[random_rows], **{**defaults, **kargs})
            if not kde:
                # g = g.map_offdiag(plt.scatter, s=3)
                g = g.map_upper(plt.scatter, s=3)
                g = g.map_diag(plt.hist, edgecolor=None, alpha=0.75)
            else:
                g = g.map_upper(plt.scatter, s=3)
                g = g.map_lower(sns.kdeplot, linewidths=1)
                g = g.map_diag(sns.kdeplot, lw=2, legend=False)
            g = g.add_legend()
        return g

def scaler(m, style="whitegrid", plot_kw=None, subplot_kw=None, **kwargs):
    """Plot the scaler properties

    Parameters
    ----------
    m: PCM class instance

    """
    # Check if the PCM is trained:
    validation.check_is_fitted(m, 'fitted')

    # Plot
    with sns.axes_style(style):
        defaults = {'sharey':'row', 'figsize':(10, 5*m.F), 'dpi':80, 'facecolor':'w', 'edgecolor':'k'}
        if not subplot_kw:
            fig, ax = plt.subplots(ncols=2, nrows=m.F, **{**defaults, **kwargs})
        else:
            fig, ax = plt.subplots(ncols=2, nrows=m.F, **{**defaults, **kwargs}, subplot_kw=subplot_kw)

        if m.F == 1:
            ax = ax[np.newaxis, :]

        for (feature, irow) in zip(m._props['features'], np.arange(0, m.F)):

            X_ave = m._scaler[feature].mean_
            X_std = m._scaler[feature].scale_
            X_unit = m._scaler_props[feature]['units']
            feature_axis = m._props['features'][feature]
            feature_name = [feature]

            # Is this a thick array or a slice ?
            is_slice = np.all(m._props['features'][feature] == None)

            if not is_slice:
                defaults_mean = {'linewidth': 2, 'label': 'Sample Mean'}
                defaults_std = {'linewidth': 2, 'label': 'Sample Std'}
                if not plot_kw:
                    ax[irow, 0].plot(X_ave, feature_axis,  **defaults_mean)
                    ax[irow, 1].plot(X_std, feature_axis, **defaults_std)

                else:
                    ax[irow, 0].plot(X_ave, feature_axis,  **{**defaults_mean, **plot_kw})
                    ax[irow, 1].plot(X_std, feature_axis, **{**defaults_std, **plot_kw})

                # tidy up the figure
                ax[irow, 0].set_ylabel('Vertical feature axis')
                for ix in range(0, 2):
                    ax[irow, ix].legend(loc='lower right')
                    ax[irow, ix].set_xlabel("[%s]" % X_unit)
                    ax[irow, ix].set_title("%s scaler" % feature, fontsize=10)
            else:
                ax[irow, 0].set_title("%s scaler mean=%f" % (feature, X_ave), fontsize=10)
                ax[irow, 1].set_title("%s scaler std=%f" % (feature, X_std), fontsize=10)

    return fig, ax

def reducer(m, pcalist=None, style="whitegrid", maxcols=np.Inf, plot_kw=None, subplot_kw=None, **kwargs):
    """ Plot PCM reducer properties """

    # Check if the PCM is trained:
    validation.check_is_fitted(m, 'fitted')

    # Plot
    with sns.axes_style(style):
        defaults = {'sharey': 'row', 'figsize': (5*m.F, 5), 'dpi': 80, 'facecolor': 'w', 'edgecolor': 'k'}
        if not subplot_kw:
            if maxcols == np.Inf:
                fig, ax = m.plot.subplots(K=m.F, maxcols=m.F, **{**defaults, **kwargs})
            else:
                fig, ax = m.plot.subplots(K=m.F, maxcols=maxcols, **{**defaults, **kwargs})
        else:
            if maxcols == np.Inf:
                fig, ax = m.plot.subplots(K=m.F, maxcols=m.F, **{**defaults, **kwargs}, subplot_kw=subplot_kw)
            else:
                fig, ax = m.plot.subplots(K=m.F, maxcols=maxcols, **{**defaults, **kwargs}, subplot_kw=subplot_kw)


        for (feature, icol) in zip(m._props['features'], np.arange(0, m.F)):
            ax[icol].set_title(feature, fontsize=10)

            if isinstance(m._reducer[feature], sklearn.decomposition.pca.PCA):
                X_eof = m._reducer[feature].components_
                if pcalist is None:
                    pcalist = range(0, X_eof.shape[0])
                if np.max(pcalist) > X_eof.shape[0]:
                    raise ValueError("PCA number %i is not available in reduced %s" % (np.max(pcalist),feature))
                feature_axis = m._props['features'][feature]
                feature_axis_name = 'Vertical feature axis'
                feature_name = [feature]
                for ic in pcalist:
                    defaults = {'linewidth': 1, 'label': 'EOF #%i' % ic}
                    if not plot_kw:
                        ax[icol].plot(X_eof[ic, :], feature_axis, **defaults)
                    else:
                        ax[icol].plot(X_eof[ic, :], feature_axis, **{**defaults, **plot_kw})

                # tidy up the figure
                ax[icol].axvline(x=0, color='k')
                ax[icol].legend(loc='lower right')
                if icol == 0:
                    ax[icol].set_ylabel(feature_axis_name)
            elif isinstance(m._reducer[feature], pcmodel.NoTransform):
                ax[icol].set_title('No reducer for %s' % feature, fontsize=10)
            else:
                ax[icol].set_title('Unknown reducer for %s !' % feature, fontsize=10)

    return fig, ax

def quant(m, da, xlim=None,
          classdimname='pcm_class',
          quantdimname = 'quantile',
          maxcols=3, cmap=None, **kwargs):
    """Plot the q-th quantiles of a dataArray for each PCM component

    Parameters
    ----------
    m: PCM class instance

    da: :class:`xarray.DataArray` with quantiles

    xlim

    classdimname

    quantdimname

    maxcols

    Returns
    -------
    fig : :class:`matplotlib.pyplot.figure.Figure`

    ax : :class:`matplotlib.axes.Axes` object or array of Axes objects.
        *ax* can be either a single :class:`matplotlib.axes.Axes` object or an
        array of Axes objects if more than one subplot was created.  The
        dimensions of the resulting array can be controlled with the squeeze
        keyword.
    """

    # Check if the PCM is trained:
    validation.check_is_fitted(m, 'fitted')

    # da must be 3D with a dimension for: CLASS, QUANTILES and a vertical axis
    # The QUANTILES dimension is called "quantile"
    # The CLASS dimension is identified as the one matching m.K length.
    if classdimname in da.dims:
        CLASS_DIM = classdimname
    elif (np.argwhere(np.array(da.shape) == m.K).shape[0] > 1):
        raise ValueError("Can't distinguish the class dimension from the others")
    else:
        CLASS_DIM = da.dims[np.argwhere(np.array(da.shape) == m.K)[0][0]]
    QUANT_DIM = quantdimname
    VERTICAL_DIM = list(set(da.dims) - set([CLASS_DIM]) - set([QUANT_DIM]))[0]

    nQ = len(da[QUANT_DIM]) # Nb of quantiles
    cmapK = m.plot.cmap() # cmap_discretize(plt.cm.get_cmap(name='Paired'), m.K)
    if not cmap:
        cmap = cmap_discretize(plt.cm.get_cmap(name='brg'), nQ)

    defaults =  {'figsize':(10, 8), 'dpi':80, 'facecolor':'w', 'edgecolor':'k'}
    fig, ax = m.plot.subplots(maxcols=maxcols, **{**defaults, **kwargs})
    if not xlim:
        xlim = np.array([0.9 * da.min(), 1.1 * da.max()])
    for k in m:
        Qk = da.loc[{CLASS_DIM:k}]
        for (iq, q) in zip(np.arange(nQ), Qk[QUANT_DIM]):
            Qkq = Qk.loc[{QUANT_DIM:q}]
            ax[k].plot(Qkq.values.T, da[VERTICAL_DIM], label=("%0.2f") % (Qkq[QUANT_DIM]), color=cmap(iq))
        ax[k].set_title(("Component: %i") % (k), color=cmapK(k))
        ax[k].legend(loc='lower right')
        ax[k].set_xlim(xlim)
        ax[k].set_ylim(np.array([da[VERTICAL_DIM].min(), da[VERTICAL_DIM].max()]))
        # ax[k].set_xlabel(Q.units)
        if k == 0: ax[k].set_ylabel('feature dimension')
        ax[k].grid(True)
    plt.tight_layout()

    return fig, ax


