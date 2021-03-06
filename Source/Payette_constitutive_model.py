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

"""Main constitutive model class file."""

import os
import imp
import re
import warnings
import math
import numpy as np

import Source.__runopts__ as ro
import Source.Payette_tensor as pt
import Source.Payette_utils as pu
import Source.Payette_xml_parser as px
from Source.Payette_xml_parser import XMLParserError as XMLParserError
from Source.Payette_unit_manager import UnitManager as UnitManager
from Source.Payette_input_parser import I_EQ


class ConstitutiveModelPrototype(object):
    """Prototype class from which constutive models are derived

    Public Methods
    --------------
    __init__
    set_up
    update_state
    finish_setup
    register_parameter
    get_parameter_names_and_values
    get_parameter_names
    parse_parameters
    parse_user_params
    initialize_state
    compute_init_jacobian
    jacobian

    """

    def __init__(self, control_file, *args, **kwargs):
        """Initialize the ConstitutiveModelPrototype object.

        The __init__ functions should be called by each constituve model that
        derives from the ConstitutiveModelPrototype base class.

        Parameters
        ----------
        control file : str
          path to the material control file
        *args : list, optional
        **kwargs : dict, optional
          keys
          code : string
            code type specified by user

        """

        # location of control file - if any
        self.control_file = control_file

        # read in the control file
        self.xml_obj = px.XMLParser(self.control_file)
        info = self.xml_obj.get_payette_info()
        self.name, self.aliases, self.material_type, source_types = info

        if not isinstance(self.aliases, (list, tuple)):
            self.aliases = [self.aliases]

        # which code to use
        if not isinstance(source_types, (list, tuple)):
            source_types = [source_types]
        self.code = kwargs.get("code")
        if self.code is None:
            self.code = source_types[0]
        elif self.code not in source_types:
            pu.report_and_raise_error(
                "requested code type {0} not supported by {1}"
                .format(self.code, self.name))

        pu.log_message("using {0} implementation of the '{1}' constitutive model"
                       .format(self.code, self.name))

        # specialized models
        if self.material_type is None:
            self.material_type = "eos"
        self.electric_field_model = (
            "electromechanical" in self.material_type.lower())
        self.eos_model = "eos" in self.material_type.lower()

        # data to be initialized later
        self.registered_params = []
        self.registered_param_idxs = []
        self.registered_params_and_aliases = []
        self.parameter_table = {}
        self.user_input_params = []
        self.parameter_table_idx_map = {}
        self.nprop = 0
        self.ndc = 0
        self.nxtra = 0
        self.J0 = None
        self.ui0 = np.zeros(self.nprop)
        self.ui = np.zeros(self.nprop)
        self.dc = np.zeros(self.ndc)
        self.bulk_modulus = 0.
        self.shear_modulus = 0.
        self._xtra_registered = False
        self._initial_density = 1.

        # Dummy place holders
        self._pi, self._xi = pu.DummyHolder(), pu.DummyHolder()

        pass

    def set_up(self, *args):
        """ set up model """
        pu.report_and_raise_error(
            'Constitutive model must provide set_up method')
        return

    def update_state(self, *args):
        """ update state """
        pu.report_and_raise_error(
            'Constitutive model must provide update_state method')
        return

    def finish_setup(self, matdat):
        """ check that model is properly set up """

        if pu.error_count():
            pu.report_and_raise_error("previously encountered parsing errors")

        if not any(self.ui):
            pu.report_and_raise_error("empty ui array")

        if self.eos_model:
            # mss: do something here? But is seems unnecessary.
            return

        if not self.bulk_modulus:
            pu.report_and_raise_error("bulk modulus not defined")

        if not self.shear_modulus:
            pu.report_and_raise_error("shear modulus not defined")

        if self.J0 is None:
            self.compute_init_jacobian()

        if not any(x for y in self.J0 for x in y):
            pu.report_and_raise_error("iniatial Jacobian is empty")

        matdat.register("jacobian", "Matrix", iv=self.J0,
                        units="NO_UNITS")
        ro.set_global_option("EFIELD_SIM", self.electric_field_model)

        if matdat.nxtra():
            for i, k in enumerate(matdat.xtra_keys()):
                setattr(self._xi, k.upper(), i)
                continue

        # initial density
        try:
            rho = self.ui0[self._pi._DENSITY]
        except AttributeError:
            rho = 1.
        if abs(rho) > pu.EPSILON:
            self._initial_density = rho

        self.matdat = matdat

        return

    def register_parameters_from_control_file(self):
        """Register parameters from the control file """
        params = self.xml_obj.get_sorted_parameters()
        for idx, pm in enumerate(params):
            self.register_parameter(
                pm["name"], idx, aliases=pm["aliases"],
                default=pm["default"], parseable=pm["parseable"],
                units=pm["units"])
            continue
        return

    def register_parameter(self, param_name, param_idx, aliases=None,
                           parseable=True, default=0., units=None,
                           description="No description available"):
        """Register parameters from the material model to the consitutive
        model base class

        Parameters
        ----------
        param_name : str
          paramter name
        param_idx : int
          index of where the parameter is located in the material user input
          array
        aliases : list
          list of aliases
        parseable : bool
          Boolean of whether the user input is read in from the input file
        default : float
          default value
        description : str
          long description of parameter

        """

        if aliases is None:
            aliases = []

        if units is None or not UnitManager.is_valid_units(units):
            pu.report_and_raise_error(
                "Units '{0}' for {1} is not valid.'".format(units, param_name))

        if not isinstance(param_name, str):
            pu.report_and_raise_error(
                "parameter name must be a string, got {0}".format(param_name))

        if not isinstance(param_idx, int):
            pu.report_and_raise_error(
                "parameter index must be an int, got {0}".format(param_idx))

        if not isinstance(aliases, list):
            pu.report_and_raise_error(
                "aliases must be a list, got {0}".format(aliases))

        # register full name, low case name, and aliases
        full_name = param_name
        param_name = param_name.lower().replace(" ", "_")
        param_names = [param_name]
        param_names.extend([x.lower().replace(" ", "_") for x in aliases])

        dupl_name = [x for x in param_names
                     if x in self.registered_params_and_aliases]

        if dupl_name:
            pu.report_error(
                "duplicate parameter names: {0}".format(", ".join(param_names)))

        if param_idx in self.registered_param_idxs:
            pu.report_error(
                "duplicate ui location [{0}] in parameter table"
                .format(", ".join(param_names)))

        self.registered_params.append(full_name)
        self.registered_params_and_aliases.extend(param_names)
        self.registered_param_idxs.append(param_idx)

        # populate parameter_table
        self.parameter_table[full_name] = {"name": full_name,
                                           "names": param_names,
                                           "ui pos": param_idx,
                                           "units": units,
                                           "parseable": parseable,
                                           "default value": default,
                                           "description": description, }
        self.parameter_table_idx_map[param_idx] = full_name
        self.nprop += 1

        # the self._pi object holds the param index
        for name in param_names:
            setattr(self._pi, name.upper(), param_idx)
            if name in ("density", "rho", "rho0"):
                setattr(self._pi, "_DENSITY", param_idx)
            continue

        return

    def ensure_all_parameters_have_valid_units(self):
        """Returns nothing if all parameters have valid units.
        Fails otherwise."""
        for param, param_dict in self.parameter_table.items():
            if not UnitManager.is_valid_units(param_dict['units']):
                pu.report_and_raise_error(
                    "Parameter does not have valid units set:\n" +
                    "\n".join(["({0}:{1})".format(x, y) for x, y in param_dict.iteritems()]))
        return

    def get_parameter_names_and_values(self, default=True, version=None):
        """Returns a 2D list of names and values
               [ ["name",  "description",  val],
                 ["name2", "description2", val2],
                 [...] ]
        """
        table = [None] * self.nprop
        if version is None:
            if default:
                version = "default"
            else:
                version = "modified"

        if version not in ("default", "unmodified", "modified",):
            pu.report_and_raise_error(
                "unrecognized version {0}".format(version))

        for param, param_dict in self.parameter_table.items():
            idx = param_dict["ui pos"]
            if version == "default":
                val = param_dict["default value"]
            elif version == "modified":
                val = self.ui[idx]
            else:
                val = self.ui0[idx]

            desc = param_dict["description"]
            table[idx] = [param, desc, val]
        return table

    def parameter_index(self, name):
        return getattr(self._pi, name.upper(), None)

    def parameter_name(self, idx):
        return self.parameter_table_idx_map.get(idx)

    def get_parameter_names(self, aliases=False):
        """Returns a list of parameter names, and optionally aliases"""
        param_names = [None] * self.nprop
        for param, pdict in self.parameter_table.items():
            idx = pdict["ui pos"]
            param_names[idx] = pdict["names"] if aliases else param
        return param_names

    def parse_parameters(self, *args):
        """ populate the materials ui array from the self.params dict """

        self.ui0 = np.zeros(self.nprop)
        self.ui = np.zeros(self.nprop)
        for param, param_dict in self.parameter_table.items():
            idx = param_dict["ui pos"]
            self.ui0[idx] = param_dict["default value"]
            self.ui[idx] = param_dict["default value"]
            continue

        # we have the name and value, now we need to get its position in the
        # ui array
        ignored, not_parseable = [], []
        for (param, param_val) in self.user_input_params:
            # %tjf: ignore units for now
            if param.lower() == "units":
                continue

            for key, val in self.parameter_table.items():
                if param.lower() in val["names"]:
                    param_name = key
                    break
                continue

            else:
                ignored.append(param)
                continue

            if not self.parameter_table[param_name]["parseable"]:
                not_parseable.append(param)
                continue

            ui_idx = self.parameter_table[param_name]["ui pos"]
            self.ui0[ui_idx] = param_val
            continue

        if ignored:
            pu.log_warning(
                "ignoring unregistered parameters: {0}"
                .format(", ".join(ignored)))
        if not_parseable:
            pu.log_warning("ignoring unparseable parameters: {0}"
                           .format(", ".join(not_parseable)))

        return

    def parse_user_params(self, user_params):
        """ read the user params and populate user_input_params """
        if not user_params:
            pu.report_and_raise_error("no parameters found")
            return 1

        errors = 0
        for line in user_params.split("\n"):
            line = re.sub(I_EQ, " ", line)
            if not line.split():
                continue

            # look for user specified materials from the material and matlabel
            # shortcuts
            matlabel = re.search(r"(?i)\bmaterial\s|\bmatlabel\s", line)
            if matlabel:
                if self.control_file is None:
                    pu.report_and_raise_error(
                        "Requested matlabel but {0} does not provide a "
                        "material data file".format(self.name))

                matlabel = line[matlabel.end():].strip()
                if not matlabel:
                    pu.report_and_raise_error("Empty matlabel encountered")

                # matlabel found, now parse the file for names and values
                matdat = self.parse_mtldb_file(material=matlabel)
                for name, val in matdat:
                    self.user_input_params.append((name.upper(), val))
                    continue

                continue

            line = line.split()
            name, val = "_".join(line[:-1]), line[-1]
            if not name:
                errors += 1
                pu.log_warning(
                    "No value for parameter '{0}' found".format(val))
                continue

            try:
                # Horrible band-aid for poorly formatted fortran output.
                # when it meant 1.0E+100, it spit out 1.0+100
                if val.endswith("+100") and "E" not in val:
                    val = float(val.replace("+100", "E+100"))
                else:
                    val = float(val)
            except ValueError:
                errors += 1
                pu.log_warning(
                    "could not convert {0} for parameter {1} to float"
                    .format(val, name))
                continue

            self.user_input_params.append((name.upper(), val))
            continue

        if errors:
            pu.report_and_raise_error("stopping due to previous errors")

        return

    def initialize_state(self, *args):
        """initialize the material state"""
        pass

    def compute_init_jacobian(self, simdat=None, matdat=None, isotropic=True):
        '''
        NAME
           compute_init_jacobian

        PURPOSE
           compute the initial material Jacobian J = dsig / dE, assuming
           isotropy
        '''
        if isotropic:
            j_0 = np.zeros((6, 6))
            threek, twog = 3. * self.bulk_modulus, 2. * self.shear_modulus
            poissons = (threek - twog) / (2. * threek + twog)
            const_1 = (1 - poissons) / (1 + poissons)
            const_2 = poissons / (1 + poissons)

            # set diagonal
            for i in range(3):
                j_0[i, i] = threek * const_1
            for i in range(3, 6):
                j_0[i, i] = twog

            # off diagonal
            (j_0[0, 1], j_0[0, 2],
             j_0[1, 0], j_0[1, 2],
             j_0[2, 0], j_0[2, 1]) = [threek * const_2] * 6
            self.J0 = np.array(j_0)

            return

        else:
            # material is not isotropic, numerically compute the jacobian
            V = [0, 1, 2, 3, 4, 5]
            self.J0 = self.jacobian(simdat, matdat, V)
            return

        return

    def jacobian(self, simdat, matdat, V):
        """Numerically compute and return a specified submatrix, Js, of the
        Jacobian matrix J = J_ij = dsigi / dE.

        Parameters
        ----------
        simdat : object
          simulation data container
        matdat : object
          material data container

        Returns
        -------
        Js : array_like
          Jacobian of the deformation J = dsig / dE

        Notes
        -----
        The submatrix returned is the one formed by the intersections of the
        rows and columns specified in the vector subscript array, v. That is,
        Js = J[v, v]. The physical array containing this submatrix is
        assumed to be dimensioned Js[nv, nv], where nv is the number of
        elements in v. Note that in the special case v = [1,2,3,4,5,6], with
        nv = 6, the matrix that is returned is the full Jacobian matrix, J.

        The components of Js are computed numerically using a centered
        differencing scheme which requires two calls to the material model
        subroutine for each element of v. The centering is about the point eps
        = epsold + d * dt, where d is the rate-of-strain array.

        History
        -------
        This subroutine is a python implementation of a routine by the same
        name in Tom Pucick's MMD driver.

        Authors
        -------
        Tom Pucick, original fortran implementation in the MMD driver
        Tim Fuller, Sandial National Laboratories, tjfulle@sandia.gov
        """

        # local variables
        nV = len(V)
        dE, Js = math.sqrt(np.finfo(np.float).eps), np.zeros((nV, nV))
        dt = simdat.get("time step")
        dt = 1 if dt == 0. else dt
        D = matdat.get("rate of deformation", copy=True)
        F0 = matdat.get("deformation gradient", copy=True)

        for i in range(nV):
            # perturb forward
            Dp = np.array(D)
            Dp[V[i]] = D[V[i]] + (dE / dt) / 2.
            Fp = F0 + pt.dot(Dp, F0) * dt
            matdat.store("rate of deformation", Dp)
            matdat.store("deformation gradient", Fp)
            self.update_state(simdat, matdat)
            Pp = matdat.get("stress", copy=True)
            matdat.restore()

            # perturb backward
            Dm = np.array(D)
            Dm[V[i]] = D[V[i]] - (dE / dt) / 2.
            Fm = F0 + pt.dot(Dm, F0) * dt
            matdat.store("rate of deformation", Dm)
            matdat.store("deformation gradient", Fm)
            self.update_state(simdat, matdat)
            Pm = matdat.get("stress", copy=True)
            matdat.restore()

            # compute component of jacobian
            Js[i, :] = (Pp[V] - Pm[V]) / dE
            continue

        return Js

    def parse_mtldb_file(self, material=None):
        """Parse the material database file

        Parameters
        ----------
        material : str, optional
          name of material

        Returns
        -------
        mtldat : list
          list of tuples of (name, val) pairs

        """
        import Source.Payette_xml_parser as px
        xml_obj = px.XMLParser(self.control_file)
        if material is None:
            try:
                mtldat = xml_obj.get_parameterized_materials()
            except XMLParserError as error:
                pu.report_and_raise_error(error.message)
        else:
            try:
                mtldat = xml_obj.get_material_parameterization(material)
            except XMLParserError as error:
                pu.report_and_raise_error(error.message)

        return mtldat

    def initial_density(self):
        """return the initial density"""
        return self._initial_density

    def parameter_indices(self):
        return self._pi

    def parameter(self, _id, val=None):
        if isinstance(_id, int):
            idx = _id
        else:
            idx = self.parameter_index(_id)
            if idx is None:
                pu.report_and_raise_error("{0} not in user input".format(_id))
        if idx > len(self.ui):
            pu.report_and_raise_error(
                "user input index {0} out of range".format(_id))
        if val is not None:
            self.ui[idx] = float(val)
        return self.ui[idx]

    def xtra_indices(self):
        return self._xi

    def xtra_index(self, name):
        return getattr(self._xi, name.upper(), None)

    def xtra(self, _id=None):
        if _id is None:
            return self.matdat.get("__xtra__")
        if isinstance(_id, int):
            idx = _id
        else:
            idx = self.xtra_index(_id)
            if idx is None:
                pu.report_and_raise_error("{0} not an xtra var".format(_id))
        return self.matdat.get("__xtra__")[idx]

    # The methods below are going to be depricated in favor of
    # under_score_separated names. We keep them here for compatibility.
    def parseParameters(self, *args):
        """docstring"""
        self.parse_parameters(*args)
        return

    def setUp(self, *args, **kwargs):
        """docstring"""
        self.set_up(*args, **kwargs)
        return

    def updateState(self, *args):
        """docstring"""
        self.update_state(*args)
        return

    def registerParameter(self, *args):
        """docstring"""
        self.register_parameter(*args)
        return
