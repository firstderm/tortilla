import torch
import time
import os

import numpy as np

from visdom import Visdom
import random

from config import Config as config

"""
    Deals with all the logging and plotting
    requirements during the training
"""
class TortillaBasePlotter:
    def __init__(self,  experiment_name=None, fields=None, win=None,
                        opts={}, port=8097, server='localhost'):
        self.experiment_name = experiment_name
        self.fields = fields
        self.win = win
        self.env = self.experiment_name
        self.opts = opts
        self.default_opts = {}
        self.port = port
        self.server = server
        self.init_visdom_server()
        self.plot_initalised = False

    def init_visdom_server(self):
        self.vis = Visdom(server="http://"+self.server, port=self.port)

    def update_opts(self):
        self._opts = self.default_opts.copy()
        self._opts.update(self.opts)
        self.opts = self._opts

class TortillaLinePlotter(TortillaBasePlotter):
    def __init__(   self, experiment_name=None, fields=None,
                    title=None, opts={}, port=8097, server='localhost'):
        super(TortillaLinePlotter, self).__init__(
                    experiment_name=experiment_name, fields=fields,
                    win=title, opts=opts, port=port, server=server)

        self.default_opts = dict(
            legend = self.fields,
            showlegend = True,
            title = self.win,
            marginbottom = 50,
            marginleft = 50
        )
        self.update_opts() #merge supplied opts into default_opts

    def append_plot(self, y, t):
        """
        Args:
            y : An array or 1D np-array of size 1 x number-of-fields
            t : A floating point number representing the location along
                time-axis
        """
        y = np.array(y).reshape((1,len(self.fields)))
        t = np.array([t])

        if self.plot_initalised:
            self.vis.line(
                Y = y,
                X = t,
                win = self.win,
                env=self.env,
                update = "append",
                opts = self.opts
            )
        else:
            # Instantiate
            self.vis.line(
                Y = y,
                X = t,
                env=self.env,
                win = self.win,
                opts = self.opts
            )
            self.plot_initalised = True

    def append_plot_with_dict(self, d, t):
        """
        Args:
            d:  A dictionary containing scalar values keyed by field names
                (as specified by self.fields)
            t : As floating point number representing the location along
                time-axis
        """
        payload = np.zeros((1, len(self.fields)))
        payload[:] = np.nan
        for _key in d.keys():
            _index = self.fields.index(_key)
            if _index > -1:
                payload[0, _index] = d[_key]
        self.append_plot(payload, t)

if __name__ == "__main__":
    opts = dict(
        xlabel = "accuracy",
        ylabel = "epochs",
    )
    fields = ['top-1', 'top-2', 'top-3']
    plotter = TortillaLinePlotter(
                        experiment_name="test-experiment",
                        fields=fields,
                        title='test-plot',
                        opts = opts
                        )
    # for _idx, _t in enumerate(range(100)):
    #     plotter.append_plot(np.random.randn(len(fields)), _t)

    for _idx, _t in enumerate(range(100)):
        _d = {}
        _d["top-1"] = np.random.randn(1)[0]
        _d["top-2"] = np.random.randn(1)[0]
        _d["top-3"] = np.random.randn(1)[0]
        plotter.append_plot_with_dict(_d, _t)
