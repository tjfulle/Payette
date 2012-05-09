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

import copy
import sys
import logging

from Source.Payette_utils import *

import Source.Payette_installed_materials as pim
from Source.Payette_data_container import DataContainer

class Material:
    '''
    CLASS NAME
       Material

    PURPOSE
       Material is the container for material related data for a Payette object. It
       is instantiated by the Payette object.

    DATA
       constitutiveModel: Material's constitutive model

    AUTHORS
       Tim Fuller, Sandia National Laboratories, tjfulle@sandia.gov
    '''

    def __init__(self, model_nam, user_params, *args, **kwargs ):

        iam = "Material.__init__"
        cmod = pim.PAYETTE_CONSTITUTIVE_MODELS[model_nam]["class name"]

        # instantiate the constiutive model
        self.constitutive_model = cmod(*args, **kwargs)

        # check if the model was successfully imported
        if not self.constitutive_model.imported:
            msg = ("Error importing the {0} material model.\n"
                   "If the material model is a fortran extension library, "
                   "it probably was not built correctly.\nTo check, go to "
                   "{1}/Source/Materials/Library\nand try importing "
                   "the material's extension module directly in a python "
                   "session.\nIf it does not import, you will need to rebuild "
                   "the extension module.\n"
                   "If rebuilding Payette does not fix the problem, "
                   "please contact the Payette\ndevelopers."
                   .format(self.constitutive_model.name,PC_MTLS_LIBRARY))
            reportError(iam,msg)

        self.eos_model = self.constitutive_model.eos_model

        # initialize material data container
        self.matdat = DataContainer(self.constitutive_model.name)
        self.extra_vars_registered = False

        # register default data
        register_default_data = self.register_default_data
        if self.eos_model:
            register_default_data = self.register_default_eos_data
        register_default_data()

        # set up the constitutive model
        self.constitutive_model.setUp(self.matdat, user_params)
        self.constitutive_model.finish_setup(self.matdat)
        self.constitutive_model.initialize_state(self.matdat)

        param_table = [None] * self.constitutive_model.nprop
        for key, dic in self.constitutive_model.parameter_table.items():
            idx = dic['ui pos']
            val1 = self.constitutive_model.ui0[idx]
            val2 = self.constitutive_model.ui[idx]
            param_table[idx] = {"name":key,
                                "initial value":val1,
                                "adjusted value":val2}
            continue

        # register param table
        self.matdat.registerOption("parameter table", param_table)

        pass

    def register_default_data(self):
        """Register the default data for the material """

        # register obligatory data

        # plotable data
        self.matdat.registerData("stress", "SymTensor",
                                 init_val=np.zeros(6),
                                 plot_key="sig")
        self.matdat.registerData("stress rate", "SymTensor",
                                 init_val=np.zeros(6),
                                 plot_key="dsigdt")
        self.matdat.registerData("strain","SymTensor",
                                 init_val=np.zeros(6),
                                 plot_key="strain")
        self.matdat.registerData("deformation gradient","Tensor",
                                 init_val="Identity",
                                 plot_key="F")
        self.matdat.registerData("rate of deformation","SymTensor",
                                 init_val=np.zeros(6),
                                 plot_key="d")
        self.matdat.registerData("vorticity","Tensor",
                                 init_val=np.zeros(9),
                                 plot_key="w")
        self.matdat.registerData("equivalent strain","Scalar",
                                 init_val=0.,
                                 plot_key="eqveps")
        self.matdat.registerData("permittivity","SymTensor",
                                 init_val=np.zeros(6),
                                 plot_key="permtv")
        self.matdat.registerData("electric field","Vector",
                                 init_val=np.zeros(3),
                                 plot_key="efield")

        # non-plotable data
        self.matdat.registerData("prescribed stress", "Array",
                                 init_val=np.zeros(6))
        self.matdat.registerData("prescribed stress components",
                                 "Integer Array",
                                 init_val=np.zeros(6,dtype=int))
        self.matdat.registerData("prescribed strain","SymTensor",
                                 init_val=np.zeros(6))
        self.matdat.registerData("strain rate","SymTensor",
                                 init_val=np.zeros(6))
        self.matdat.registerData("prescribed deformation gradient","Tensor",
                                 init_val=np.zeros(9))
        self.matdat.registerData("deformation gradient rate","Tensor",
                                 init_val=np.zeros(9))
        self.matdat.registerData("rotation","Tensor",
                                 init_val="Identity")
        self.matdat.registerData("rotation rate","Tensor",
                                 init_val=np.zeros(9))
        return

    def register_default_eos_data(self):
        self.matdat.registerData("density","Scalar",
                                 init_val=0.,
                                 plot_key="rho")
        self.matdat.registerData("temperature","Scalar",
                                 init_val=0.,
                                 plot_key="temp")
        self.matdat.registerData("energy","Scalar",
                                 init_val=0.,
                                 plot_key="enrg")
        self.matdat.registerData("pressure","Scalar",
                                 init_val=0.,
                                 plot_key="pres")
        pass

    def material_data(self):
        return self.matdat

    def constitutiveModel(self):
        return self.constitutive_model

    def updateState(self, simdat, matdat):
        return self.constitutive_model.updateState(simdat, matdat)

    def jacobian(self, simdat, matdat):
        return self.constitutive_model.jacobian(simdat, matdat)

