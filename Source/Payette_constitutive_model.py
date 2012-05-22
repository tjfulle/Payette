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

import numpy as np
import math
import Source.Payette_tensor as pt
import Source.Payette_utils as pu

material_idx = 0

class ConstitutiveModelPrototype(object):
    '''
    CLASS NAME
       ConstitutiveModelPrototype

    PURPOSE
       Prototype class from which constutive models are derived

    METHODS
       setField
       checkProperties
       update_state
       modelParameters
       internalStateVariables
       derivedConstants
       isvKeys

    AUTHORS
       Tim Fuller, Sandia National Laboratories, tjfulle@sandia.gov
    '''

    def __init__(self):
        self.registered_params = []
        self.registered_param_idxs = []
        self.registered_params_and_aliases = []
        self.name = None
        self.aliases = []
        self.parameter_table = {}
        self.user_input_params = {}
        self.parameter_table_idx_map = {}
        self.nprop = 0
        self.ndc = 0
        self.nxtra = 0
        self.J0 = None
        self.ui = np.zeros(self.nprop)
        self.dc = np.zeros(self.ndc)
        self.bulk_modulus = 0.
        self.shear_modulus = 0.
        self.electric_field_model = False
        self.errors = 0
        self.eos_model = False
        pass

    def set_up(self, *args):
        """ set up model """
        pu.reportError(__file__,'Constitutive model must provide set_up method')
        return

    def update_state(self, *args):
        """ update state """
        pu.reportError(__file__,'Constitutive model must provide update_state method')
        return

    def finish_setup(self, matdat):
        """ check that model is properly set up """

        name = self.name
        iam = name + ".finish_setup"

        if self.errors:
            pu.reportError(iam, "previously encountered parsing errors")

        if not any( self.ui ):
            pu.reportError(iam, "empty ui array")

        if self.eos_model:
            # mss: do something here? But is seems unnecessary.
            return

        if not self.bulk_modulus:
            pu.reportError(iam, "bulk modulus not defined")

        if not self.shear_modulus:
            pu.reportError(iam, "shear modulus not defined")

        if self.J0 is None:
            self.compute_init_jacobian()

        if not any(x for y in self.J0 for x in y):
            pu.reportError(iam, "iniatial Jacobian is empty")

        matdat.register_data("jacobian", "Matrix", init_val=self.J0)
        matdat.register_option("efield sim", self.electric_field_model)

        return

    def register_parameter(self, param_name, param_idx,
                           aliases=[], parseable=True):

        iam = self.name + ".registerParameter"
        if not isinstance(param_name,str):
            pu.reportError(iam,"parameter name must be a string, got {0}"
                        .format(param_name))

        if not isinstance(param_idx,int):
            pu.reportError(iam,"parameter index must be an int, got {0}"
                        .format(param_idx))

        if not isinstance(aliases,list):
            pu.reportError(iam,"aliases must be a list, got {0}".format(aliases))
            pass

        # register full name, low case name, and aliases
        full_name = param_name
        param_name = param_name.lower().replace(" ","_")
        param_names = [param_name]
        param_names.extend([x.lower().replace(" ","_") for x in aliases])

        dupl_name = [x for x in param_names
                     if x in self.registered_params_and_aliases]

        if dupl_name:
            pu.reportWarning(iam,"duplicate parameter names: {0}"
                          .format(", ".join(param_names)))
            self.errors += 1
            pass

        if param_idx in self.registered_param_idxs:
            pu.reportWarning(iam,"duplicate ui location [{0}] in parameter table"
                          .format(", ".join(param_names)))
            self.errors += 1

        self.registered_params.extend(full_name)
        self.registered_params_and_aliases.extend(param_names)
        self.registered_param_idxs.append(param_idx)

        # populate parameter_table
        self.parameter_table[full_name] = { "name": full_name,
                                            "names": param_names,
                                            "ui pos": param_idx,
                                            "parseable": parseable}
        self.parameter_table_idx_map[param_idx] = full_name
        return

    def get_parameter_names_and_values(self):
        """Returns a 2D list of names and values
               [ ["name", val], ["name2", val2], ... ]
        """
        table = []
        for param in self.parameter_table.keys():
            table.append([self.parameter_table[param], self.parameter_table[])
        return table

    def parse_parameters(self, *args):
        """ populate the materials ui array from the self.params dict """

        iam = self.name + ".parse_parameters"

        self.ui0 = np.zeros(self.nprop)

        # we have the name and value, now we need to get its position in the
        # ui array
        param_nam = None
        ignored, not_parseable = [], []
        for param, param_val in self.user_input_params.items():
            if param in self.parameter_table:
                param_nam = param

            else:
                # look for alias
                for key, val in self.parameter_table.items():
                    if param in val["names"]:
                        param_nam = key
                        break
                    continue

            if param_nam is None:
                ignored.append(param)
                continue

            if not self.parameter_table[param_nam]["parseable"]:
                not_parseable.append(param)
                continue

            ui_idx = self.parameter_table[param_nam]["ui pos"]
            self.ui0[ui_idx] = param_val
            continue

        if ignored:
            pu.reportWarning(iam,
                             "ignoring unregistered parameters: {0}"
                             .format(", ".join(ignored)))
        if not_parseable:
            pu.reportWarning(iam,
                             "ignoring unparseable parameters: {0}"
                             .format(", ".join(not_parseable)))

        return

    def _parse_user_params(self, user_params):
        """ read the user params and populate user_input_params """
        iam = self.name + "._parse_user_params"

        if not user_params:
            pu.reportError(iam, "no parameters found")
            return 1

        errors = 0
        for line in user_params:
            # strip and lowcase the line
            line = line.strip().lower()

            # replace "=" and "," with spaces and split
            for char in "=,":
                line = line.replace(char, " ")
                continue
            line = line.split()

            # the line is now of form
            #     line = [string, string, ..., string]
            # we assume that the last string is the value and anything up
            # to the last is the name
            name = "_".join(line[0:-1])
            val = line[-1]
            try:
                val = float(val)
            except:
                errors += 1
                msg = ("could not convert {0} for parameter {1} to float"
                       .format(val, name))
                pu.reportWarning(iam, msg)
                continue

            self.user_input_params[name] = val
            continue

        if errors:
            pu.reportError(iam, "stopping due to previous errors")

        return

    def initialize_state(self, material_data):
        pass

    def initialParameters(self):
        return self.ui0

    def checkedParameters(self):
        return self.ui

    def modelParameters(self):
        return self.ui

    def initialJacobian(self):
        return self.J0

    def internalStateVariables(self):
        return self.sv

    def derivedConstants(self):
        return self.dc

    def isvKeys(self):
        return self.keya

    def compute_init_jacobian(self,simdat=None,matdat=None,isotropic=True):
        '''
        NAME
           compute_init_jacobian

        PURPOSE
           compute the initial material Jacobian J = dsig/deps, assuming
           isotropy
        '''
        if isotropic:
            J0 = np.zeros((6, 6))
            threek, twog = 3. * self.bulk_modulus, 2. * self.shear_modulus
            pr = (threek - twog) / (2. * threek + twog)
            c1,c2 = (1-pr)/(1+pr), pr/(1+pr)
            for i in range(3): J0[i,i] = threek*c1
            for i in range(3, 6): J0[i,i] = twog
            (          J0[0, 1], J0[0, 2],
             J0[1, 0],           J0[1, 2],
             J0[2, 0], J0[2, 1]           ) = [threek * c2] * 6
            self.J0 = np.array(J0)
            return

        else:
            # material is not isotropic, numerically compute the jacobian
            matdat.stash_data("prescribed stress components")
            matdat.store_data("prescribed stress components",[0,1,2,3,4,5])
            self.J0 = self.jacobian(simdat, matdat)
            matdat.unstash_data("prescribed stress components")
            return

        return


    def jacobian(self, simdat, matdat):
        '''
        NAME
           jacobian

        PURPOSE:
           Numerically compute and return a specified submatrix, Jsub, of the
           Jacobian matrix J = J_ij = dsigi/depsj. The submatrix returned is the
           one formed by the intersections of the rows and columns specified in
           the vector subscript array, v. That is, Jsub = J[v,v]. The physical
           array containing this submatrix is assumed to be dimensioned
           Jsub[nv,nv], where nv is the number of elements in v. Note that in the
           special case v = [1,2,3,4,5,6], with nv = 6, the matrix that is
           returned is the full Jacobian matrix, J.

           The components of Jsub are computed numerically using a centered
           differencing scheme which requires two calls to the material model
           subroutine for each element of v. The centering is about the point eps
           = epsold + d * dt, where d is the rate-of-strain array.

        INPUT:
           dt:   timestep
           d:    symmetric part of velocity gradient
           sig:  stress
           sv:   state variables
           v:     v
           args: not used
           kwargs: not used

        OUTPUT
           J: Jacobian of the deformation J = dsig/deps

        HISTORY
           This subroutine is a python implementation of a routine by the same name
           in Tom Pucick's MMD driver.

        AUTHORS
           Tom Pucick, original fortran implementation in the MMD driver
           Tim Fuller, Sandial National Laboratories, tjfulle@sandia.gov
        '''
    # local variables
        epsilon = 2.2e-16
        v = matdat.get_data("prescribed stress components")
        nv = len(v)
        deps,Jsub = math.sqrt(epsilon),np.zeros((nv,nv))

        dt = simdat.get_data("time step")
        d = matdat.get_data("rate of deformation")
        Fold = matdat.get_data("deformation gradient",form="Matrix")
        dtime = 1 if dt == 0. else dt

        # stash the data
        simdat.stash_data("time step")
        matdat.stash_data("rate of deformation")
        matdat.stash_data("deformation gradient")

        for n in range(nv):
            # perturb forward
            dp = np.array(d)
            dp[v[n]] = d[v[n]] + (deps/dtime)/2.
            fp = Fold + np.dot(pt.to_matrix(dp),Fold)*dtime
            matdat.store_data("rate of deformation",dp,old=True)
            matdat.store_data("deformation gradient",fp,old=True)
            self.update_state(simdat, matdat)
            sigp = matdat.get_data("stress",cur=True)

            # perturb backward
            dm = np.array(d)
            dm[v[n]] = d[v[n]] - (deps/dtime)/2.
            fm = Fold + np.dot(pt.to_matrix(dm),Fold)*dtime
            matdat.store_data("rate of deformation",dm,old=True)
            matdat.store_data("deformation gradient",fm,old=True)
            self.update_state(simdat, matdat)
            sigm = matdat.get_data("stress",cur=True)

            Jsub[n,:] = (sigp[v] - sigm[v])/deps
            continue

        # restore data
        simdat.unstash_data("time step")
        matdat.unstash_data("deformation gradient")
        matdat.unstash_data("rate of deformation")

        return Jsub

    # The methods below are going to be depricated in favor of
    # under_score_separated names. We keep them here for compatibility.
    def parseParameters(self, *args):
        self.parse_parameters(*args)
        return
    def setUp(self, *args, **kwargs):
        """ set up model """
        self.set_up(*args, **kwargs)
        return
    def updateState(self, *args):
        self.update_state(*args)
        return
    def registerParameter(self, *args):
        self.register_parameter(*args)
        return



