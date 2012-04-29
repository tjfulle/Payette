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


#from __future__ import print_function
import os
import sys
import re
import imp
import math
import numpy as np
import time

from Source.Payette_utils import *
from Source.Payette_material import Material
from Source.Payette_data_container import DataContainer
import Source.Payette_installed_materials as pim
import Source.Payette_driver as cdriver


PARSE_ERRORS = 0


def parser_error(msg):
    global PARSE_ERRORS
    print("ERROR: {0:s}".format(msg))
    PARSE_ERRORS += 1
    sys.exit(101)
    return


class Payette:
    """
    CLASS NAME
       Payette

    PURPOSE
       main container class for a Payette single element simulation, instantiated in
       the runPayette script. The documentation is currently sparse, but may be
       expanded if time allows.

    AUTHORS
       Tim Fuller, Sandia National Laboratories, tjfulle@sandia.gov
    """

    def __init__(self, simname, user_input, opts):

        iam = simname + ".__init__"

        if opts.debug:
            opts.verbosity = 4
        loglevel = opts.verbosity

        delete = not opts.keep
        basedir = os.getcwd()

        self.name = simname

        # check user input for required blocks
        if "material" not in user_input:
            parser_error("material block not found in input file")

        if "boundary" not in user_input:
            parser_error("boundary block not found in input file")

        if "legs" not in user_input:
            parser_error("legs block not found in input file")

        outfile = os.path.join(basedir, simname + ".out")
        if delete and os.path.isfile(outfile):
            os.remove(outfile)

        elif os.path.isfile(outfile):
            i = 0
            while True:
                outfile = os.path.join(basedir, "%s.%i.out" % (simname, i))
                if os.path.isfile(outfile):
                    i += 1
                    if i > 100:
                        parser_error("Come on!  Really, over 100 output files???")

                    else:
                        continue
                else:
                    break
                continue

        # logfile
        logfile = "{0}.log".format(os.path.splitext(outfile)[0])
        try:
            os.remove(logfile)
        except OSError:
            pass

        setupLogger(logfile,loglevel)

        msg = "setting up simulation {0}".format(simname)
        reportMessage(iam, msg)

        # file name for the Payette restart file
        rfile = "{0}.prf".format(os.path.splitext(outfile)[0])

        # set up the simulation data container
        self.simdat = DataContainer(simname)

        # --- register obligatory data
        # plotable data
        self.simdat.registerData("time","Scalar",
                                 init_val = 0.,
                                 plot_key="time")
        self.simdat.registerData("time step","Scalar",
                                 init_val = 0.,
                                 plot_key = "timestep")
        self.simdat.registerData("number of steps","Scalar",
                                 init_val = 0)
        self.simdat.registerData("strain","SymTensor",
                                 init_val = np.zeros(6),
                                 plot_key = "strain")
        self.simdat.registerData("deformation gradient","Tensor",
                                 init_val = "Identity",
                                 plot_key = "F")
        self.simdat.registerData("rate of deformation","SymTensor",
                                 init_val = np.zeros(6),
                                 plot_key = "d")
        self.simdat.registerData("vorticity","Tensor",
                                 init_val = np.zeros(9),
                                 plot_key = "w")
        self.simdat.registerData("equivalent strain","Scalar",
                                 init_val = 0.,
                                 plot_key = "eqveps")
        self.simdat.registerData("permittivity","SymTensor",
                                 init_val = np.zeros(6),
                                 plot_key = "permtv")
        self.simdat.registerData("electric field","Vector",
                                 init_val = np.zeros(3),
                                 plot_key = "efield")

        # non-plotable data
        self.simdat.registerData("prescribed stress","Array",
                                 init_val = np.zeros(6))
        self.simdat.registerData("prescribed stress components","Integer Array",
                                 init_val = np.zeros(6,dtype=int))
        self.simdat.registerData("prescribed strain","SymTensor",
                                 init_val = np.zeros(6))
        self.simdat.registerData("strain rate","SymTensor",
                                 init_val = np.zeros(6))
        self.simdat.registerData("prescribed deformation gradient","Tensor",
                                 init_val = np.zeros(9))
        self.simdat.registerData("deformation gradient rate","Tensor",
                                 init_val = np.zeros(9))
        self.simdat.registerData("rotation","Tensor",
                                 init_val = "Identity")
        self.simdat.registerData("rotation rate","Tensor",
                                 init_val = np.zeros(9))

        # set up simulation from user input
        self.material = None
        self.lcontrol = None
        self.bcontrol = None

        self.boundaryFactory(user_input["boundary"], user_input["legs"])
        self.materialFactory(user_input["material"])

        # get mathplot
        mathplot = user_input.get("mathplot")
        plotable = []
        if mathplot is not None:
            for item in mathplot["content"]:
                for pat, repl in ((",", " "), (";", " "), (":", " "), ):
                    item = item.replace(pat, repl)
                    continue
                plotable.extend(item.split())
                continue

        # get extraction
        extraction = user_input.get("extraction")
        extract = []
        if extraction is not None:
            for item in extraction["content"]:
                for pat, repl in ((",", " "), (";", " "), (":", " "), ):
                    item = item.replace(pat, repl)
                    continue
                item = item.split()
                for x in item:
                    if x[0] not in ("%", "@"):
                        msg = "unrecognized extraction request {0}".format(x)
                        reportWarning(iam, msg)
                        continue
                    extract.append(x)
                continue

        # register boundary variables
        self.simdat.registerData("leg number","Scalar", init_val=0 )

        self.simdat.registerData("leg data","List",
                                 init_val = self.lcontrol)

        # check if user has specified simulation options
        for item in user_input["content"]:
            deprication_warning = False
            for pat, repl in ((",", " "), (";", " "), (":", " "), ):
                item = item.replace(pat, repl)
                continue
            item = item.split()

            if item[0] == "title": deprication_warning = True

            if deprication_warning:
                msg = ("depricated input file option [{0}] skipped"
                       .format(item[0]))
                reportWarning(iam, msg)
                continue

            if len(item) == 1:
                item.append("True")

            try:
                val = eval(item[1])

            except:
                val = str(item[1])

            self.simdat.registerOption(item[0], val)
            continue

        # register some obligatory options
        self.simdat.registerOption("simname",simname)
        self.simdat.registerOption("outfile",outfile)
        self.simdat.registerOption("logfile",logfile)
        self.simdat.registerOption("loglevel",loglevel)
        self.simdat.registerOption("restart file",rfile)
        self.simdat.registerOption("verbosity",opts.verbosity)
        self.simdat.registerOption("sqa",opts.sqa)
        self.simdat.registerOption("write vandd table",opts.write_vandd_table)
        self.simdat.registerOption("use table",opts.use_table)
        self.simdat.registerOption("debug",opts.debug)
        self.simdat.registerOption("test restart",opts.testrestart)
        self.simdat.registerOption("initial time",self.t0)
        self.simdat.registerOption("termination time",self.tf)
        self.simdat.registerOption("kappa",self.bcontrol["kappa"])
        self.simdat.registerOption("emit",self.bcontrol["emit"])
        self.simdat.registerOption("screenout",self.bcontrol["screenout"])
        self.simdat.registerOption("nprints",self.bcontrol["nprints"])
        self.simdat.registerOption("legs",self.lcontrol)
        self.simdat.registerOption("material",self.material)
        self.simdat.registerOption("efield sim",self.material.electricFieldModel())
        self.simdat.registerOption("mathplot vars",[x.upper() for x in plotable])
        self.simdat.registerOption("extraction",[x.upper() for x in extract])
        self.simdat.registerOption("math1",
                                   os.path.join(basedir, simname + ".math1"))
        self.simdat.registerOption("math2",
                                   os.path.join(basedir, simname + ".math2"))

        # Below are obligatory options that may have been specified in the
        # input file.
        if "proportional" not in self.simdat.getAllOptions():
            self.simdat.registerOption("proportional",False)
            pass

        if "strict" not in self.simdat.getAllOptions():
            self.simdat.registerOption("strict",False)
            pass

        if "nowriteprops" not in self.simdat.getAllOptions():
            self.simdat.registerOption("nowriteprops", opts.nowriteprops)

        if "norestart" in self.simdat.getAllOptions():
            self.simdat.registerOption("write restart",False)
        else:
            self.simdat.registerOption("write restart",not opts.norestart)

        # write out properties
        if not self.simdat.NOWRITEPROPS:
            self.writeMaterialParameters()

        # if the material does not support electric fields, remove the electric
        # field data from the simdat data container, we must register and then
        # unregister because at the time that the material model is instantiated,
        # we do not know if it supports electric fields. Those models that do
        # support electric fields need to know the initial value at setup.
        if not self.simdat.EFIELD_SIM:
            self.simdat.unregisterData("electric field")
            self.simdat.unregisterData("permittivity")

        pass


    def materialFactory(self, material_inp):
        """
        NAME
           materialFactory

        PURPOSE
           Read material block from input file, parse it, and create material
           object

        AUTHORS
           Tim Fuller, Sandia National Laboratories, tjfulle@sandia.gov
        """

        material = material_inp["content"]

        # check for required input
        constitutive_model = None
        f_params = None
        mf_index = None
        user_params = []
        for item in material:
            if "constitutive model" in item:
                # line defines the constitutive model, get the name of the model
                # to be used
                constitutive_model = item[len("constitutive model"):].strip()
                pass

            elif "material" in item:
                parser_error("material keyword depricated")

                # below is old code for the material input file that is a python
                # file that defines a material based on common names. I might
                # resurrect this in the future, thus I am leaving it.
                m = item[len("material"):].strip()
                fdir,fname = os.path.split(m)
                mname,fext = os.path.splitext(fname)
                if fext:
                    if fext != ".py":
                        parser_error(
                            "material database file must be a python file, "
                            "got {0}".format(m))
                        return 1
                    else: pass
                else: fname = m + ".py"

                # material database directories
                lpd = payetteParametersDir()

                # check if material database file is in:
                f = None
                if os.path.isfile(os.path.join(fdir,fname)): # given directory
                    f = os.path.join(fdir,fname)

                elif os.path.isfile(os.path.join(os.getcwd(),fname)): # cwd
                    f = os.path.join(os.getcwd(),fname)

                elif os.path.isfile(os.path.join(lpd,fname)): #lpd
                    f = os.path.join(lpd,fname)

                else:
                    msg = ("{0} material file {1} not found in [{2}, {3}, {4}]"
                           .format(mname, fname, fdir, os.getcwd(), lpd))
                    parser_error(msg)

                try:
                    f_params = imp.load_source(mname, f).parameters

                except:
                    parser_error("unable to load material parameters from {0}"
                                 .format(f))

            else:
                user_params.append(item)

            continue

        # check that the constitutive model is defined in the input file.
        if not constitutive_model:
            # constitutive model not given, exit
            parser_error("no constitutive model in material block")

        # constitutive model given, now see if it is available, here we replace
        # spaces with _ in all model names and convert to lower case
        mdlname = constitutive_model.lower().replace(" ","_")
        available_models = pim.PAYETTE_CONSTITUTIVE_MODELS
        for key in available_models:
            if mdlname == key or mdlname in available_models[key]["aliases"]:
                constitutive_model = key

            continue

        # we have done a case insensitive check, replaced spaces with _ and
        # checked aliases, if the model is still not in the available models,
        # bail
        if constitutive_model not in available_models:
            parser_error("constitutive model {0} not installed"
                         .format(constitutive_model))

        # instantiate the material object
        self.material = Material(
            constitutive_model, self.simdat, user_params, f_params)

        return

    def boundaryFactory(self, boundary_inp, legs_inp):
        """
        NAME
           boundaryFactory

        PURPOSE
           scan the user input for a begin boundary .. end boundary block
           and parse it

        AUTHORS
           Tim Fuller, Sandia National Laboratories, tjfulle@sandia.gov
        """

        iam = self.name + "boundaryFactory"

        nodeBoundary_cache = {}
        elementBoundary_cache = {}

        boundary = boundary_inp["content"]
        legs = legs_inp["content"]

        # parse boundary
        bcontrol = {"kappa":0.,"estar":1.,"tstar":1.,"ampl":1.,"efstar":1.,
                    "ratfac":1.,"sstar":1.,"fstar":1.,"dstar":1.,
                    "emit":"all","nprints":0,"stepstar":1,"screenout":False}
        for item in boundary:
            item = item.replace("="," ")
            try:
                kwd, val = item.split()
            except:
                parser_error("boundary control items must be "
                             "keword = value pairs")

            try:
                kwd, val = kwd.strip(),float(eval(val))
            except:
                kwd, val = kwd.strip(),str(val)

            if kwd in bcontrol.keys():
                bcontrol[kwd] = val

            else:
                continue

            continue

        if bcontrol["emit"] not in ("all", "sparse"):
            parser_error("emit must be one of [all,sparse]")

        if bcontrol["screenout"]:
            bcontrol["screenout"] = True

        if not isinstance(bcontrol["nprints"], int):
            bcontrol["nprints"] = int(bcontrol["nprints"])

        if not isinstance(bcontrol["stepstar"], (float,int)):
            bcontrol["stepstar"] = max(0.,float(bcontrol["stepstar"]))

        if bcontrol["stepstar"] <= 0:
            parser_error("stepstar must be > 0.")

        # the following are from Brannon's MED driver
        # estar is the "unit" of strain
        # sstar is the "unit" of stress
        # fstar is the "unit" of deformation gradient
        # efstar is the "unit" of electric field
        # dstar is the "unit" of electric field
        # tstar is the "unit" of time
        # All strains are multiplied by efac=ampl*estar
        # All stresses are multiplied by sfac=ampl*sstar
        # All deformation gradients are multiplied by ffac=ampl*fstar
        # All electric fields are multiplied by effac=ampl*efstar
        # All displacements are multiplied by dfac=ampl*dstar
        # All times are multiplied by tfac=abs(ampl)*tstar/ratfac
        # From these formulas, note that AMPL may be used to increase or decrease
        # the peak strain without changing the strain rate. ratfac is the
        # multiplier on strain rate and stress rate.
        bcontrol["tfac"] = (abs(bcontrol["ampl"]) *
                            bcontrol["tstar"] / bcontrol["ratfac"])
        bcontrol["efac"] = bcontrol["ampl"] * bcontrol["estar"]
        bcontrol["sfac"] = bcontrol["ampl"] * bcontrol["sstar"]
        bcontrol["ffac"] = bcontrol["ampl"] * bcontrol["fstar"]
        bcontrol["effac"] = bcontrol["ampl"] * bcontrol["efstar"]
        bcontrol["dfac"] = bcontrol["ampl"] * bcontrol["dstar"]

        # parse legs
        lcontrol = []
        kappa = bcontrol["kappa"]
        sigc = False

        # control should be a group of letters describing what type of
        # control type the leg is. valid options are:
        #  1: strain rate control
        #  2: strain control
        #  3: stress rate control
        #  4: stress control
        #  5: deformation gradient control
        #  6: electric field
        #  8: displacement
        for ileg, leg in enumerate(legs):

            leg = [x.strip() for x in leg.replace(","," ").split() if x]

            if ileg == 0:
                g_inf = parse_first_leg(leg)

                if g_inf["table"]:
                    # the first leg let us know the user specified a table,
                    # continu on to the actual table
                    g_leg_no = 0
                    g_time = 0.
                    continue

            if g_inf["table"]:
                if leg[0].lower() == "time":
                    # table could have
                    continue

                control = g_inf["control"]
                leg_steps = int(bcontrol["stepstar"])
                leg_no = g_leg_no
                g_leg_no += 1
                if g_inf["ttyp"] == "dt":
                    g_time += float(leg[g_inf["col_idxs"][0]])
                else:
                    g_time = float(leg[g_inf["col_idxs"][0]])

                leg_t = bcontrol["tfac"] * g_time
                try:
                    cij = [float(eval(leg[x])) for x in g_inf["col_idxs"][1:]]
                except:
                    parser_error("syntax error in leg {0}".format(leg[0]))

            else:
                if len(leg) < 5:
                    parser_error(
                        "leg {0} input must be of form:".format(leg[0]) +
                        "\n       leg number, time, steps, type, c[ij]")
                leg_no = int(float(leg[0]))
                leg_t = bcontrol["tfac"] * float(leg[1])
                leg_steps = int(bcontrol["stepstar"] * float(leg[2]))
                if ileg != 0 and leg_steps == 0:
                    parser_error("leg number {0} has no steps".format(leg_no))

                control = leg[3].strip()
                try:
                    cij = [float(eval(y)) for y in leg[4:]]
                except:
                    parser_error("syntax error in leg {0}".format(leg[0]))

            # control should be a group of letters describing what type of
            # control type the leg is. valid options are:
            #  1: strain rate control
            #  2: strain control
            #  3: stress rate control
            #  4: stress control
            #  5: deformation gradient control
            #  6: electric field
            #  8: displacement
            allwd_cntrl = "1234568"
            if [x for x in control if x not in allwd_cntrl]:
                parser_error("leg control parameters can only be one of "
                             "[{0}] got {1} for leg number {2:d}"
                             .format(allwd_cntrl, control, leg_no))

            if not sigc:
                sigc = bool([x for x in control if x == "3" or x == "4"])

            lcntrl = [int(x) for x in list(control)]

            if len(lcntrl) != len(cij):
                parser_error("length of leg control != number of control "
                             "items in leg {0:d}".format(leg_no))

            # separate out electric fields from deformations
            ef, hold, efcntrl = [], [], []
            for i, j in enumerate(lcntrl):
                if j == 6:
                    ef.append(cij[i])
                    hold.append(i)
                    efcntrl.append(j)
                continue
#            if ef and sigc: parser_error("Stress and electric field control not "
#                                     "allowed simulataneously")

            ef.extend([0.] * (3 - len(ef)))
            efcntrl.extend([6] * (3 - len(efcntrl)))
            cij = [i for j, i in enumerate(cij) if j not in hold]
            lcntrl = [i for j, i in enumerate(lcntrl) if j not in hold]

            if len(lcntrl) != len(cij):
                parser_error("final length of leg control != number of "
                             "control items in leg {0:d}".format(leg_no))

            reduced_lcntrl = list(set(lcntrl))
            if 5 in reduced_lcntrl:
                # deformation gradient control check
                if len(reduced_lcntrl) != 1:
                    parser_error("only components of deformation gradient "
                                 "are allowed with deformation gradient "
                                 "control in leg {0:d}, got {1}"
                                 .format(leg_no, control))

                elif len(cij) != 9:
                    parser_error("all 9 components of deformation gradient "
                                 "must be specified for leg {0:d}"
                                 .format(leg_no))

                else:
                    # check for valid deformation
                    F = np.array([[cij[0], cij[1], cij[2]],
                                  [cij[3], cij[4], cij[5]],
                                  [cij[6], cij[7], cij[8]]])
                    J = np.linalg.det(F)
                    if J <= 0:
                        parser_error("inadmissible deformation gradient in leg "
                                     "{0:d} gave a Jacobian of {1:f}"
                                     .format(leg_no, J))

                    # convert F to strain E with associated rotation given by
                    # axis of rotation x and angle of rotation theta
                    R,V = np.linalg.qr(F)
                    U = np.dot(R.T,F)
                    if np.max(np.abs(R - np.eye(3))) > epsilon():
                        parser_error(
                            "rotation encountered in leg {0}. ".format(leg_no) +
                            "rotations are not yet supported")

            elif 8 in reduced_lcntrl:
                # displacement control check
                if len(reduced_lcntrl) != 1:
                    parser_error("only components of displacment are allowed "
                                 "with displacment control in leg {0:d}, got {1}"
                                 .format(leg_no, control))
                    pass

                elif len(cij) != 3:
                    parser_error("all 3 components of displacement must "
                                 "be specified for leg {0:d}".format(leg_no))

                # convert displacments to strains
                dfac = bcontrol["dfac"]
                # Seth-Hill generalized strain is defined
                # strain = (1/kappa)*[(stretch)^kappa - 1]
                # and
                # stretch = displacement + 1

                # In the limit as kappa->0, the Seth-Hill strain becomes
                # strain = ln(stretch).
                for j in range(3):
                    stretch = dfac * cij[j] + 1
                    if kappa != 0:
                        cij[j] = 1 / kappa * (stretch ** kappa - 1.)
                    else:
                        cij[j] = math.log(stretch)
                    continue

                # displacements now converted to strains
                lcntrl = [2, 2, 2]
                pass

            if lcntrl == [2]:

                # only one strain value given -> volumetric strain
                ev = cij[0] * bcontrol["efac"]
                if kappa * ev + 1. < 0.:
                    parser_error("1 + kappa*ev must be positive")

                if kappa == 0.:
                    ev = ev / 3.
                else:
                    ev = ((kappa * ev + 1.) ** (1. / 3.) - 1.) / kappa

                lcntrl = [2, 2, 2]
                cij = [ev, ev, ev]
                efac_hold = bcontrol["efac"]
                bcontrol["efac"] = 1.0

            for i, j in enumerate(lcntrl):
                if j == 1 or j == 3:
                    cij[i] = bcontrol["ratfac"] * cij[i]

                elif j == 2:
                    cij[i] = bcontrol["efac"] * cij[i]
                    if kappa * cij[i] + 1. < 0.:
                        parser_error("1 + kappa*c[{0:d}] must be positive"
                                     .format(i))

                elif j == 4:
                    cij[i] = bcontrol["sfac"] * cij[i]

                elif j == 5:
                    cij[i] = bcontrol["ffac"] * cij[i]

                elif j == 6:
                    cij[i] = bcontrol["effac"] * cij[i]
                    pass

                continue

            try:
                bcontrol["efac"] = efac_hold
            except:
                pass

            # fill in cij and lcntrl so that their lengths are always 9
            cij.extend([0.] * (9 - len(cij)))
            lcntrl.extend([0] * (9 - len(lcntrl)))

            # append leg control
            # the electric field control is added to the end of lcntrl
            lcontrol.append([leg_no,
                             leg_t,
                             leg_steps,
                             lcntrl + efcntrl,
                             np.array(cij + ef)])
            continue

        if sigc:
            # stress and or stress rate is used to control this leg. For
            # these cases, kappa is set to 0. globally.
            if kappa != 0.:
                reportWarning(
                    iam,
                    "WARNING: stress control boundary conditions "
                    "only compatible with kappa=0. kappa is being "
                    "reset to 0. from %f\n"%kappa)
                bcontrol["kappa"] = 0.
                pass

        # check that time is monotonic in lcontrol
        i = -0.001
        self.t0 = None
        for leg in lcontrol:
            if self.t0 == None: self.t0 = leg[1]
            if leg[1] < i:
                print(leg[1],i)
                print(leg)
                parser_error("time must be monotonic in from {0:d} to {1:d}"
                             .format(int(leg[0] - 1), int(leg[0])))
                pass
            i = leg[1]
            self.tf = leg[1]
            continue
        self.lcontrol = lcontrol
        self.bcontrol = bcontrol
        return

    def finish(self):

        # close the log and output files
        closeFiles()

        matdat = self.material.materialData()
        # write the mathematica files
        if self.simdat.MATHPLOT_VARS:
            writeMathPlot(self.simdat, matdat)

        # extract requested variables
        if self.simdat.EXTRACTION:
            write_extraction(self.simdat, matdat)

        return

    def simulationData(self):
        return self.simdat

    def writeMaterialParameters(self):
        with open( self.simdat.SIMNAME + ".props", "w" ) as f:
            matdat = self.material.materialData()
            for item in matdat.PARAMETER_TABLE:
                key = item["name"]
                val = item["adjusted value"]
                f.write("{0:s} = {1:12.5E}\n".format(key,val))
                continue
            pass
        return

    def setupRestart(self):
        iam = self.name + "setupRestart"
        setupLogger(self.simdat.LOGFILE,self.simdat.LOGLEVEL,mode="a")
        msg = "setting up simulation %s"%self.simdat.SIMNAME
        reportMessage(iam, msg)

def parse_first_leg(leg):
    """Parse the first leg of the legs block.

    The first leg of the legs block may be in one of two forms.  The usual

              <leg_no>, <leg_t>, <leg_steps>, <leg_cntrl>, <c[ij]>

    or, if the user is prescribing the legs through a table

              using <time, dt>, <deformation type> [from columns ...]

    here, we determine what kind of legs the user is prescrbing.

    Parameters
    ----------
    leg: list
        First leg in the legs block of the user input

    Returns
    -------
    leg_inf: dict

    Raises
    ------

    See also
    --------

    Notes
    -----

    Examples
    --------
    >>> parse_first_leg([0, 0., 0, 222222, 0, 0, 0, 0, 0, 0])
    {"table": False}

    >>> parse_first_leg(["using", "dt", "strain"])
    {"table": True, "ttyp": "dt", "deftyp": "strain", "len": 6,
     "colidx": range(7)}

    >>> parse_first_leg(["using", "dt", "strain", "from", "columns", "1:7"])
    {"table": True, "ttyp": "dt", "deftyp": "strain", "len": 6,
     "colidx": range(7)}

    >>> parse_first_leg(["using", "dt", "stress", "from",
                         "columns", "1,2,3,4,5,6,7"])
    {"table": True, "ttyp": "dt", "deftyp": "strain", "len": 6,
     "colidx": range(7)}

    >>> parse_first_leg(["using", "dt", "strain", "from", "columns", "1-7"])
    {"table": True, "ttyp": "dt", "deftyp": "strain", "len": 6,
     "colidx": range(7)}

    >>> parse_first_leg(["using", "dt", "strain", "from", "columns", "1,5-10"])
    {"table": True, "ttyp": "dt", "deftyp": "strain", "len": 6,
     "colidx": [0,4,5,6,7,8,9,20]}

    >>> parse_first_leg(["using", "dt", "strain", "from", "columns", "1,5-7"])
    {"table": True, "ttyp": "dt", "deftyp": "strain", "len": 6,
     "colidx": [0,4,5,6]}

    """

    errors = 0
    allowed_legs = {
        "strain rate": {"num": 1, "len": 6},
        "strain": {"num": 2, "len": 6},
        "stress rate": {"num": 3, "len": 6},
        "stress": {"num": 4, "len": 6},
        "deformation gradient": {"num": 5, "len": 9},
        "electric field": {"num": 6, "len": 3},
        "displacement": {"num": 8, "len": 3},
        "vstrain": {"num": 2, "len": 1}}
    allowed_t = ["time", "dt"]

    if "using" not in leg[0]:
        return {"table": False}

    t_typ = leg[1]

    if t_typ not in allowed_t:
        errors += 1
        msg = ("requested bad time type {0} in {1}, expected one of [{2}]"
               .format(t_typ, leg, ", ".join(allowed_t)))
        parser_error(msg)

    col_spec =[x for x in leg[2:] if "from" in x or "column" in x]

    if not col_spec:
        # default value for col_idxs
        use_typ = " ".join(leg[2:])
        if use_typ not in allowed_legs:
            parser_error("requested bad control type {0}".format(use_typ))

        col_idxs = range(allowed_legs[use_typ]["len"] + 1)

    elif col_spec and len(col_spec) != 2:
        # user specified a line of the form
        # using <dt,time> <deftyp> from ...
        # or
        # using <dt,time> <deftyp> columns ...
        msg = ("expected {0} <deftyp> from columns ..., got {1}"
               .format(t_typ, leg))
        parser_error(msg)

    else:
        use_typ = " ".join(leg[2:leg.index(col_spec[0])])
        if use_typ not in allowed_legs:
            parser_error("requested bad control type {0}".format(use_typ))

        # now we need to find the column indexes
        col_idxs = " ".join(leg[leg.index(col_spec[-1]) + 1:])
        col_idxs = col_idxs.replace("-", ":")

        if ":" in col_idxs.split():
            tmpl = col_idxs.split()

            # user may have specified something like 1 - 6 which would now be
            # 1 : 6, which is a bad range specifier, we need to fix it
            idx = tmpl.index(":")

            if len(tmpl) == 3 and idx == 1:
                # of form: from columns 1:7
                col_idxs = "".join(tmpl)

            elif len(tmpl) == 4 and idx != 2:
                # of form: from columns 1:6, 7 -> not allowed
                parser_error("bad column range specifier in: '{0}'"
                             .format(" ".join(leg)))

            elif len(tmpl) == 4:
                # of form: from columns 1, 2:7
                col_idxs = tmpl[0] + " " + "".join(tmpl[1:])

        if col_idxs.count(":") > 1:
            # only one range allowed
            parser_error("only one column range supported".format(use_typ))

        col_idxs = col_idxs.split()
        if len(col_idxs) == 1 and not [x for x in col_idxs if ":" in x]:
            # of form: from columns 8 -> not allowed
            parser_error("not enough columns specified in: '{0}'"
                         .format(" ".join(leg)))

        elif len(col_idxs) == 1 and [x for x in col_idxs if ":" in x]:
            # of form: from columns 2:8
            col_idxs = col_idxs[0].split(":")
            col_idxs = range(int(col_idxs[0]) - 1, int(col_idxs[1]))

        elif len(col_idxs) == 2 and [x for x in col_idxs if ":" in x]:
            # specified a single index and range
            if col_idxs.index([x for x in col_idxs if ":" in x][0]) != 1:
                # of form: from columns 2:8, 1 -> not allowed
                parser_error("bad column range specifier in: '{0}'"
                             .format(" ".join(leg)))
            else:
                # of form: from columns 1, 2:8
                tmp = col_idxs[1].split(":")
                col_idxs = [int(col_idxs[0]) - 1]
                col_idxs.extend(range(int(tmp[0]) - 1, int(tmp[1])))
        else:
            # specified all columns individually, convert to 0 index
            col_idxs = [int(x) - 1 for x in col_idxs]

        # we have now parsed the first line, assemble leg_ing
        if len(col_idxs) > allowed_legs[use_typ]["len"] + 1:
            parser_error("too many columns specified")

    # we have exhausted all ways of specifying columns that I can think of,
    # save the info and return
    leg_inf = {
        "table": True,
        "col_idxs": col_idxs,
        "ttyp": t_typ,
        "deftyp": use_typ,
        "len": allowed_legs[use_typ]["len"],
        "control":("{0}".format(allowed_legs[use_typ]["num"])
                   * allowed_legs[use_typ]["len"])
        }

    return leg_inf

if __name__ == "__main__":
    sys.exit("Payette_container.py must be called by runPayette")
