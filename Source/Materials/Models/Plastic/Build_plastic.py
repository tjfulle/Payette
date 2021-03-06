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

import os
import sys
from shutil import copyfile

import Source.__config__ as cfg
from Source.Payette_material_builder import MaterialBuilder
from Source.Payette_utils import PayetteError as PayetteError


class Build(MaterialBuilder):

    def __init__(self, name, libname, libdir, compiler_info):

        fdir, fnam = os.path.split(os.path.realpath(__file__))

        # initialize base class
        srcd = fdir
        sigf = os.path.join(fdir, "Payette_plastic.pyf")
        MaterialBuilder.__init__(
            self, name, libname, srcd, libdir, compiler_info, sigf=sigf)

        pass

    def build_extension_module(self):

        # fortran files
        eos_file = os.getenv("EOS_MODULI_FILE")
        if eos_file is None:
            eos_file = os.path.join(self.source_directory, "plastic_eos.f90")

        tens_tools = os.path.join(cfg.FORTRAN, "tensor_toolkit.f90")
        self.source_files.extend([tens_tools, eos_file])
        f_srcs = ["plastic_mod.f90", "plastic.f90"]
        self.source_files.extend([os.path.join(self.source_directory, x)
                                  for x in f_srcs])

        try:
            retval = self.build_extension_module_with_f2py()

        except PayetteError as error:
            sys.stderr.write("ERROR: {0}".format(error.message))
            retval = error.errno

        return retval
