# Copyright (2011) Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

# The MIT License

# Copyright (c) Sandia Corporation

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

"""Contains classes and functions for writing index files for permutation and
optimization simulations

"""
import os
import sys
import imp

try:
    import cPickle as pickle
except ImportError:
    import pickle

import Source.__config__ as cfg
import Source.Payette_utils as pu
import Source.__runopts__ as ro


class ModelIndex(object):
    """Class for indexing installed materials

    """
    def __init__(self, index_file=None):
        """Initialize the ModelIndex object

        Parameters
        ----------
        self : class instance

        """

        # index file name
        if index_file is None:
            index_file = ro.MTLDB

        index_dir = os.path.dirname(index_file)
        if not os.path.isdir(index_dir):
            pu.report_and_raise_error(
                "Directory {0} must first be created".format(index_dir))
        self.index_file = index_file

        # initialize class data
        self._installed_constitutive_models = {}

        # load the index file if it exists
        if os.path.isfile(self.index_file):
            self.load()

    def remove_model(self, model):
        """remove model from the index"""
        try:
            del self._installed_constitutive_models[model]
        except KeyError:
            pass
        return

    def constitutive_models(self):
        """return the installed constitutive models dict"""
        return self._installed_constitutive_models.keys()

    def store(self, name, libname, libdir, clsname, intrfc, cntrl, aliases,
              param_file=None, param_cls=None):
        """Store all kwargs in to the index dict

        Parameters
        ----------
        name : str
          material name
        libname : str
          library name
        libdir : str
          directory where library is located
        clsname : str
          material class name
        intrfc : str
          absolute path to interface file
        cntrl : str
          absolute path to .xml control file
        aliases : list
          list of alternative names for the model
        """

        self._installed_constitutive_models[name] = {
            "libname": libname, "class name": clsname,
            "interface file": intrfc, "control file": cntrl,
            "aliases": aliases, "libdir": libdir,
            "parameterization file": param_file,
            "parameterization class": param_cls, }

        return

    def dump(self):
        """Dump self.constitutive_models to a file"""
        # dup the index file
        if cfg.ROOT in self.index_file:
            stubf = "PAYETTE_ROOT" + self.index_file.split(cfg.ROOT)[1]
        else:
            stubf = self.index_file
        pu.log_message("writing constitutive model information to: {0}"
                       .format(stubf), beg="\n")
        with open(self.index_file, "wb") as fobj:
            pickle.dump(self._installed_constitutive_models, fobj)
        pu.log_message("constitutive model information written\n")
        return

    def load(self):
        """Load the index file"""
        # check existence of file
        if not os.path.isfile(self.index_file):
            pu.report_and_raise_error(
                "buildPayette must be executed to generate {0}"
                .format(self.index_file))
        # load it in
        self._installed_constitutive_models = pickle.load(
            open(self.index_file, "rb"))
        return self._installed_constitutive_models

    def constitutive_model(self, model_name):
        """ get the constitutive model dictionary of model_name """
        for key, val in self._installed_constitutive_models.items():
            if model_name.lower() == key.lower() or model_name in val["aliases"]:
                constitutive_model = val
                break
            continue

        else:
            pu.report_and_raise_error(
                "constitutive model {0} not found, installed models are: {1}"
                .format(model_name, ", ".join(self.constitutive_models())))

        return constitutive_model

    def control_file(self, model_name):
        """ get the control file for the material """
        constitutive_model = self.constitutive_model(model_name)
        return constitutive_model.get("control file")

    def library_directory(self, model_name):
        """ get the library directory for the material """
        constitutive_model = self.constitutive_model(model_name)
        return constitutive_model.get("libdir")

    def constitutive_model_object(self, model_name):
        """ get the actual model object """
        constitutive_model = self.constitutive_model(model_name)
        sys.path.insert(0, constitutive_model.get("libdir"))
        py_mod, py_path = pu.get_module_name_and_path(
            constitutive_model["interface file"])
        cls_nam = constitutive_model["class name"]
        fobj, pathname, description = imp.find_module(py_mod, py_path)
        py_module = imp.load_module(py_mod, fobj, pathname, description)
        fobj.close()
        version = getattr(py_module, "PAYETTE_VERSION", None)
        if version is None:
            pu.report_and_raise_error(
                "PAYETTE_VERSION attribute missing from the "
                "material model interface file")
        # --- legacy support -> version now a tuple
        try:
            version = tuple(version.split("."))
        except AttributeError:
            pass

        major, minor = version[:2]
        M, m = cfg.VERSION_INFO[:2]
        if (major, minor) < (M, m):
            pu.report_and_raise_error(
                "Material model '{0}' requires Payette version {1}.{2}"
                .format(model_name, major, minor))
        cmod = getattr(py_module, cls_nam)
        del py_module
        return cmod

    def parameterization_file(self, model_name):
        """ get the parameterize file for the material """
        constitutive_model = self.constitutive_model(model_name)
        return constitutive_model.get("parameterization file")

    def parameterizer(self, model_name):
        """ get the actual model object """
        constitutive_model = self.constitutive_model(model_name)
        if constitutive_model["parameterization file"] is None:
            return None
        py_mod, py_path = pu.get_module_name_and_path(
            constitutive_model["parameterization file"])
        cls_nam = constitutive_model["parameterization class"]
        fobj, pathname, description = imp.find_module(py_mod, py_path)
        py_module = imp.load_module(py_mod, fobj, pathname, description)
        fobj.close()
        _parameterizer = getattr(py_module, cls_nam)
        del py_module
        return _parameterizer


def remove_index_file():
    """remove the index file"""
    try:
        os.remove(ro.MTLDB)
    except OSError:
        pass
    return
