# The MIT License

# Copyright (c) 2011 Tim Fuller

# License for the specific language governing rights and limitations under
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
"""Payette_optimize.py module. Contains classes and functions for optimizing
parameters using Payette.

"""

import os, sys
import numpy as np
import scipy
import scipy.optimize

import Source.Payette_utils as pu
import Source.Payette_extract as pe
import Source.Payette_input_parser as pip
import Source.Payette_model_index as pmi
import Source.runopts as ro
import Toolset.KayentaParamConv as kpc
from Source.Payette_extract import ExtractError as ExtractError

# Module level variables
IOPT = 0
EPS = np.finfo(np.float).eps
PDAT = np.array([-7.15e8, 1.2231e-10, 1.28e-18, .084])

class ParameterizeError(Exception):
    def __init__(self, message):
        super(ParameterizeError, self).__init__(message)

class ParameterizeLogger(object):
    loggers = {"root": None, }
    def __init__(self, name, fpath, mode="w"):
        self.name = name
        self.fpath = fpath
        self.fobj = open(fpath, mode)
        self.loggers[self.name] = {"object": self, "file object": self.fobj}
        pass

    def log(self, message, level=1, end="\n", cout=False, root_write=False):
        """Log a message

        Parameters
        ----------
        message : str
            the message to write
        level : int [optional, 1]
            log level
        end : str [optional, \n]
            ending character
        cout : bool [optional, False]
            write message to console
        """
        pre = {0: "", 1: "INFO: ", 2: "WARNING: ", 3: "ERROR: "}[level]
        message = message.split("\n")
        message = "".join(["{0}{1}{2}".format(pre, x, end)
                           for x in message if x])

        self.fobj.write(message)

        if cout or ro.VERBOSITY > 1:
            sys.stdout.write(message)

        root = self.loggers["root"].get("object")
        if self == root:
            return

        if root is not None and root_write:
            self.loggers["root"]["file object"].write(message)

        return

    def close(self):
        self.fobj.flush()
        self.fobj.close()
        del self.loggers[self.name]
        return

    def closeall(self):
        for logger in self.loggers:
            try:
                logger["file object"].flush()
                logger["file object"].close()
            except ValueError:
                pass

def get_logger(name, fpath=None):
    if fpath is not None:
        return ParameterizeLogger(name, fpath)
    logger = ParameterizeLogger.loggers.get(name)
    if logger is None:
        raise ParameterizeLogger("Logger {0} not found".format(name))
    return logger["object"]


def parameterizer(input_lines):
    r"""docstring -> needs to be completed """

    # get the optimization block
    job_inp = pip.InputParser(input_lines)

    # check for compatible constitutive model
    constitutive_model = job_inp.user_options["constitutive model"]
    model_index = pmi.ModelIndex()
    parameterizer = model_index.parameterizer(constitutive_model)
    if parameterizer is None:
        raise ParameterizeError(
            "Constitutive model {0} does not have a parameterizing "
            "module defined".format(constitutive_model))

    # check for required directives
    req_directives = ("constitutive model", "material", )
    job_directives = job_inp.input_options()
    for directive in req_directives:
        if directive not in job_directives:
            raise ParameterizeError(
                "Required directive {0} not found".format(directive))

    return parameterizer(job_inp)


class Parameterize(object):
    r"""docstring -> needs to be completed """

    def __init__(self, job, *args, **kwargs):
        r""" Initialization """

        # the name is the name of the material
        self.job_directives = job.input_options()
        self.name = self.job_directives["material"]
        self.fext = ".opt"
        self.verbosity = ro.VERBOSITY
        self.job = job

        pass

    def run_job(self):
        sys.exit("run_job method not provided")

    def finish(self):
        sys.exit("finish method not provided")

    def parse_block(self, block):
        """Parse the Kayenta parameterization blocks

        """

        # defaults
        data_f = None
        optimize = {}
        fix = {}
        options = {}

        # parse the shearfit block
        for item in block:

            for pat in ",=()":
                item = item.replace(pat, " ")
            item = item.split()

            if not item:
                continue

            token = item[0].lower()

            if " ".join(item[0:2]).lower() == "data file":
                data_f = os.path.realpath(item[2])
                if not data_f:
                    pu.report_error("data file {0} not found".format(data_f))

            elif "optimize" in token:
                # set up this parameter to optimize
                key = item[1]
                vals = item[2:]

                bounds = (None, None)
                init_val = None

                # upper bound
                if "bounds" in vals:
                    try:
                        idx = vals.index("bounds") + 1
                        bounds = [float(x) for x in vals[idx:idx+2]]
                    except ValueError:
                        pu.report_error("bounds requires 2 arguments")

                    if bounds[0] > bounds[1]:
                        pu.report_error(
                            "lower bound {0} > upper bound {1} for {2}"
                            .format(bounds[0], bounds[1], key))

                if "initial" in vals:
                    idx = vals.index("initial")
                    if vals[idx + 1] == "value":
                        idx = idx + 1
                        try:
                            init_val = float(vals[idx+1])
                        except ValueError:
                            pu.report_error("excpected float for initial value")

                optimize[key] = {"bounds": bounds, "initial value": init_val,}

            elif "fix" in token:
                # set up this parameter to fix
                key = item[1]
                vals = item[2:]
                init_val = None
                if "initial" in vals:
                    idx = vals.index("initial")
                    if vals[idx + 1] == "value":
                        idx = idx + 1
                        try:
                            init_val = float(vals[idx+1])
                        except ValueError:
                            pu.report_error("excpected float for initial value")

                fix[key] = {"initial value": init_val}

            else:
                key = token.upper()
                if len(item) == 1:
                    val = True
                else:
                    val = " ".join(item[1:])
                options[key] = val

            continue

        if data_f is None:
            pu.report_error("No data file given for shearfit problem")

        for key, val in fix.items():
            if key.lower() in [x.lower() for x in optimize]:
                pu.report_error("cannot fix and optimize {0}".format(key))

        if pu.error_count():
            pu.report_and_raise_error("stopping due to previous errors")

        return data_f, optimize, fix, options