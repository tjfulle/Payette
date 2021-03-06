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

import sys
import Source.Payette_utils as pu


class UnitManager:
    """
    CLASS NAME
       UnitManager

    PURPOSE
       To handle conversions between unit systems in a general, consistent,
       transparent, and accurate way.

    AUTHORS
       Scot Swan, Sandia National Laboratories, mswan@sandia.gov
    """

    # The dimensions must have seven dimensions (len(base_dim)==7):
    #  (0) length
    #  (1) mass
    #  (2) time
    #  (3) temperature
    #  (4) discrete amount
    #  (5) electric current
    #  (6) luminous intensity

    # All of the following systems are defined by the SI system:
    # Meters, Kilograms, Seconds, Kelvin, Mole, ampere, candella
    # Please see "Model Interface Guidelines" SAND96-2000, August 1996
    # Appendix C for more information (available from www.osti.gov/bridge/).
    valid_systems = {
        "SI": [1, 1, 1, 1, 1, 1, 1],
        "MKSK": [1, 1, 1, 1, 1, 1, 1],
        "CGSK": [0.01, 0.001, 1, 1, 1, 1, 1],
        "CGSEV": [0.01, 0.001, 1, 1.0 / 8.617343e-5, 1, 1, 1],
        "SESAME": [0.01, 0.001, 1.0e-5, 1, 1, 1, 1],
        "SHOCK": [0.01, 0.001, 1.0e-6, 8.617343e-5, 1, 1, 1]}

    # The following are aliases to define dimensions for given quantities.
    # Feel free to define your own or use "Model Interface Guidelines"
    # SAND96-2000, August 1996 Appendix B for more information (available
    # from www.osti.gov/bridge/).
    valid_dim_aliases = {
        "UNITLESS": [0, 0, 0, 0, 0, 0, 0],
        "LENGTH": [1, 0, 0, 0, 0, 0, 0],
        "MASS": [0, 1, 0, 0, 0, 0, 0],
        "TIME": [0, 0, 1, 0, 0, 0, 0],
        "TEMPERATURE": [0, 0, 0, 1, 0, 0, 0],
        "DISCRETE_AMOUNT": [0, 0, 0, 0, 1, 0, 0],
        "ELECTRIC_CURRENT": [0, 0, 0, 0, 0, 1, 0],
        "LUMINOUS_INTENSITY": [0, 0, 0, 0, 0, 0, 1],
        # Common Lambda and Alegra units
        "DENSITY_UNITS": [-3, 1, 0, 0, 0, 0, 0],
        "TEMPERATURE_UNITS": [0, 0, 0, 1, 0, 0, 0],
        "VELOCITY_UNITS": [1, 0, -1, 0, 0, 0, 0],
        "SPECIFIC_HEAT_UNITS": [2, 0, -2, -1, 0, 0, 0],
        "SPECIFIC_ENERGY_UNITS": [2, 0, -2, 0, 0, 0, 0],
        "PRESSURE_UNITS": [-1, 1, -2, 0, 0, 0, 0],
        "VISCOSITY_UNITS": [-1, 1, -1, 0, 0, 0, 0],
        "VOLUME_UNITS": [3, 0, 0, 0, 0, 0, 0],
        # Lambda units
        "NO_UNITS": [0, 0, 0, 0, 0, 0, 0],
        "INV_PRESSURE_UNITS": [1, -1, 2, 0, 0, 0, 0],
        "INV_TEMPERATURE_UNITS": [0, 0, 0, -1, 0, 0, 0],
        "INV_TIME_UNITS": [0, 0, -1, 0, 0, 0, 0],
        # Alegra units
        "NONDIMENSIONAL_UNTIS": [0, 0, 0, 0, 0, 0, 0],
        "PRESSURE_INV_UNITS": [1, -1, 2, 0, 0, 0, 0],
        "PRESSURE_OVER_LENGTH_UNITS": [-2, 1, -2, 0, 0, 0, 0],
        "PRESSURE_INV_UNITS_SQ": [2, -2, -4, 0, 0, 0, 0],
        "TIME_INV_UNITS": [0, 0, -1, 0, 0, 0, 0],
        # Suggested Lambda Units
        "LENGTH_UNITS": [1, 0, 0, 0, 0, 0, 0],
        "MASS_UNITS": [0, 1, 0, 0, 0, 0, 0],
        "TIME_UNITS": [0, 0, 1, 0, 0, 0, 0],
        "RATE_UNITS": [0, 0, -1, 0, 0, 0, 0],
        "SQUARED_INV_PRESSURE_UNITS": [2, -2, -4, 0, 0, 0, 0],
        "STIFFNESS_UNITS": [-2, 1, -2, 0, 0, 0, 0],
        "VORTICITY_UNITS": [0, 0, -1, 0, 0, 0, 0],
        # Not specified
        "NOT_SPECIFIED": [0, 0, 0, 0, 0, 0, 0],
        # non-base    m   kg  s   K   n   A   lu
        "POSITION": [1, 0, 0, 0, 0, 0, 0],
        "VELOCITY": [1, 0, -1, 0, 0, 0, 0],
        "ACCELERATION": [1, 0, -2, 0, 0, 0, 0],
        "FORCE": [1, 1, -2, 0, 0, 0, 0],
        "STRESS": [-1, 1, -2, 0, 0, 0, 0],
        "STRAIN": [0, 0, 0, 0, 0, 0, 0],
        "DENSITY": [-3, 1, 0, 0, 0, 0, 0],
        "SPECIFIC HEAT CAPACITY": [2, 0, -2, -1, 0, 0, 0],
        "VOLUME": [3, 0, 0, 0, 0, 0, 0],
        "ENERGY_UNITS": [2, 1, -2, 0, 0, 0, 0],
        "GAS_CONSTANT_UNITS": [2, 1, -2, -1, -1, 0, 0],  # energy / temp / mole
        "CAPACITANCE_UNITS": [-2, -1, 4, 0, 0, 2, 0],
        "PERMITTIVITY_UNITS": [-3, -1, 4, 0, 0, 2, 0],
        "INV_PERMITTIVITY_UNITS": [3, 1, -4, 0, 0, -2, 0],
        "RESISTANCE_UNITS": [2, 1, -3, 0, 0, -2, 0],  # Ohm
        "ELECTRIC_POTENTIAL_UNITS": [2, 1, -3, 0, 0, -1, 0],  # Volt
        "ELECTRIC_FIELD_UNITS": [1, 1, -3, 0, 0, -1, 0],  # Volt / meter
        "POLARIZATION_UNITS": [0, 0, 0, 0, 0, 0, 0],
        "INV_POLARIZATION_UNITS_SQ": [0, 0, 0, 0, 0, 0, 0],
    }

    @classmethod
    def is_valid_unit_system(cls, unit_system):
        try:
            unit_system = unit_system.upper()
            if unit_system in cls.valid_systems.keys():
                return unit_system
            else:
                return ""
        except:
            return ""

    @classmethod
    def is_valid_units(cls, units):
        if type(units) == list:
            # The list of units must have 7 integers.
            if len(units) != 7:
                return []  # evaluates to False
            if not all([type(x) == int for x in units]):
                return []  # evaluates to False
            return [x for x in units]

        elif type(units) == str:
            # If the units is just an alias, return that list
            units = units.upper()
            if units in cls.valid_dim_aliases.keys():
                return cls.valid_dim_aliases[units]

            # This looks for valid string representations of
            # units. It has an ability to do "_OVER_" for complex
            # unit types. For example, to get units for DPDRHO,
            # you could say "PRESSURE_UNITS_OVER_DENSITY_UNITS".
            units = units.split("_OVER_")
            if units[0] not in cls.valid_dim_aliases.keys():
                return []
            retunits = [x for x in cls.valid_dim_aliases[units[0]]]
            for dum in units[1:]:
                if dum not in cls.valid_dim_aliases.keys():
                    return []
                for i in range(0, 7):
                    retunits[i] -= cls.valid_dim_aliases[dum][i]
            return [x for x in retunits]
        else:
            return []

    @classmethod
    def transform(cls, value, units, input_unit_system, output_unit_system):
        a = cls(value, input_unit_system, units)
        a.convert(output_unit_system)
        return a.get()

    @classmethod
    def class_info(cls):
        # Create a string containing pretty-printed information about
        # the class (particularly the valid unit systems and dimension
        # aliases).
        class_info = ("{0:=^50}".format(" Unit Manager Class Information ") +
                      "\n\nList of valid unit systems:\n" +
                      "\n".join(["    " + x for x in cls.valid_systems.keys()]) +
                      "\n\nList of valid dimension aliases:\n" +
                      "\n".join(["    " + x for x in cls.valid_dim_aliases.keys()]) +
                      "\n")
        return class_info

    def __init__(self, value, unit_system, base_dim):
        # We must have a value that is a float or can be converted to a float.
        try:
            self.val = float(value)
        except ValueError:
            sys.exit("Cannot convert '{0}' to float.".format(value))

        # The original unit system must be a valid option.
        self.system = self.is_valid_unit_system(unit_system)
        if not self.system:
            sys.exit("Unit system '{0}' not found in {1}".
                     format(unit_system, repr(self.valid_systems.keys())))

        # Attempt to determine the common name for the dimensions given.
        self.dimensions = self.is_valid_units(base_dim)
        if not self.dimensions:
            pu.report_and_raise_error(
                "Cannot process units '{0}'".format(repr(base_dim)))

    def get(self, system=None):
        """ Return the stored value (in a different unit system, if given) """
        if system is None:
            return float(self.val)

        system = system.upper()
        if not self.is_valid_unit_system(system):
            sys.exit("Cannot convert to '{0}' - "
                     "not in list of valid systems:\n".format(system.upper()) +
                     "\n".join(self.valid_systems.keys()))
        tmp = self.val
        for idx in range(0, len(self.dimensions)):
            if self.dimensions[idx] == 0:
                continue

            curr_sys_fac = self.valid_systems[self.system][idx]
            new_sys_fac = self.valid_systems[system][idx]
            dim_exp = self.dimensions[idx]

            try:
                tmp *= (curr_sys_fac / new_sys_fac) ** dim_exp
            except:
                sys.stderr.write("{0:^79}".format(" DEBUG INFORMATION "))
                sys.stderr.write("original val = {0:.14e}".format(self.val))
                sys.stderr.write(
                    "tmp *= (curr_sys_fac / new_sys_fac) ** dim_exp")
                sys.stderr.write("dimensions   = {0}".format(self.dimensions))
                sys.stderr.write("tmp          = {0:.14e}".format(tmp))
                sys.stderr.write(
                    "curr_sys_fac = {0:.14e}".format(curr_sys_fac))
                sys.stderr.write("new_sys_fac  = {0:.14e}".format(new_sys_fac))
                sys.stderr.write("dim_exp      = {0:.14e}".format(dim_exp))
                sys.exit()

        return float(tmp)

    def convert(self, system):
        """ Convert the stored value to a different unit system """
        self.val = self.get(system=system)
        self.system = system

    def value_info(self):
        """ Return a string containing pretty-printed information """
        msg = ("value: {0}\n"
               "unit system: {1}\n"
               "dimensions:\n"
               "              length {2}\n"
               "                mass {3}\n"
               "                time {4}\n"
               "         temperature {5}\n"
               "              amount {6}\n"
               "    electric current {7}\n"
               "  luminous intensity {8}\n".
               format(self.val, self.system, *self.dimensions))
        return msg

    def update(self, newval):
        """ Overwrite the current stored value with a new value """
        self.val = newval

    def clone(self, y, copy_dim=True,
              new_dim=valid_dim_aliases["UNITLESS"]):
        """ Overwrite the current stored value with a new value """
        if copy_dim:
            return UnitManager(y, self.system, self.dimensions)
        else:
            return UnitManager(y, self.system, new_dim)

    def multiply_dimensions(self, x, y):
        return [x.dimensions[i] + y.dimensions[i] for i in range(7)]

    def divide_dimensions(self, x, y):
        return [x.dimensions[i] - y.dimensions[i] for i in range(7)]

###############################################################################
###############               FLOAT-LIKE FUNCTIONS               ##############
###############################################################################
    def __abs__(self):
        return self.clone(abs(self.get()))

    def __add__(self, y):
        if self.dimensions != y.dimensions:
            raise ValueError("'UnitManager.__add__' function cannot" +
                             " operate on 'UnitManager' types of unequal" +
                             " dimensions.\n{0} != {1}".
                             format(repr(self.dimensions), repr(y.dimensions)))
        return self.clone(self.get() + y.get())

    def __coerce__(self, y):
        new_y = y
        if new_y.__class__.__name__ != UnitManager.__name__:
            # Creates a new UnitManager object with no dimensions
            new_y = self.clone(float(y), copy_dim=False)
        if self.system != new_y.system:
            raise TypeError("Cannot perform operations on UnitManager " +
                            "objects of different unit systems.\n" +
                            "{0} != {1}".format(self.system, new_y.system))
        return (self, new_y)

    def __div__(self, y):
        new_dim = self.divide_dimensions(self, y)
        return self.clone(self.get() / y.get(),
                          copy_dim=False,
                          new_dim=new_dim)

    def __divmod__(self, y):
        if self.dimensions != y.dimensions:
            raise ValueError("'UnitManager.__divmod__' function cannot" +
                             " operate on 'UnitManager' types of unequal" +
                             " dimensions.\n{0} != {1}".
                             format(repr(self.dimensions), repr(y.dimensions)))
        raise TypeError("'UnitManager.__divmod__' not implemented.")

    def __eq__(self, y):
        return self.get() == y.get()

    def __float__(self):
        return float(self.get())

    def __floordiv__(self, y):
        raise TypeError("'UnitManager.__floordiv__' not implemented.")
        # return self.clone(self.get() // y.get())

    def __format__(self, format_sped):
        raise TypeError("'UnitManager.__format__' not implemented.")

    def __ge__(self, y):
        return self.get() >= y.get()

    def __getattribute__(self, name):
        return self.name

    def __gt__(self, y):
        return self.get() > y.get()

    def __hash__(self):
        return hash(self.get())

    def __int__(self):
        return int(self.get())

    def __le__(self, y):
        return self.get() <= y.get()

    def __long__(self):
        return long(self.get())

    def __lt__(self, y):
        return self.get() < y.get()

    def __mod__(self, y):
        if self.dimensions != y.dimensions:
            raise ValueError("'UnitManager.__mod__' function cannot" +
                             " operate on 'UnitManager' types of unequal" +
                             " dimensions.\n{0} != {1}".
                             format(repr(self.dimensions), repr(y.dimensions)))
        return self.clone(self.get() % y.get())

    def __mul__(self, y):
        new_dim = self.multiply_dimensions(self, y)
        return self.clone(self.get() * y.get(),
                          copy_dim=False,
                          new_dim=new_dim)

    def __ne__(self, y):
        return self.get() != y.get()

    def __neg__(self):
        return self.clone(-abs(self.get()))

    def __nonzero__(self):
        return self.get() != 0

    def __pos__(self):
        return self.clone(abs(self.get()))

    def __pow__(self, *args):
        raise TypeError("'UnitManager.__pow__' not implemented because" +
                        " applying arbitrary powers to values with units" +
                        " opens a giant can of worms that really shouldn't" +
                        " be forced on anyone. Please, just say x*x or" +
                        " 1.0/(x*x) etc. for your powers.")
        # return self.clone(pow(self.get(), args))

    def __radd__(self, y):
        if self.dimensions != y.dimensions:
            raise ValueError("'UnitManager.__radd__' function cannot" +
                             " operate on 'UnitManager' types of unequal" +
                             " dimensions.\n{0} != {1}".
                             format(repr(self.dimensions), repr(y.dimensions)))
        return self.clone(self.get() + y.get())

    def __rdiv__(self, y):
        new_dim = self.divide_dimensions(y, self)
        return self.clone(y.get() / self.get(),
                          copy_dim=False,
                          new_dim=new_dim)

    def __rdivmod__(self, y):
        raise TypeError("'UnitManager.__rdivmod__' not implemented.")
        # return self.clone(divmod(y.get(), self.get()))

    def __repr__(self):
        return self.value_info()

    def __rfloordiv__(self, y):
        raise TypeError("'UnitManager.__rfloordiv__' not implemented.")
        # return self.clone(y.get() // self.get())

    def __rmod__(self, y):
        if self.dimensions != y.dimensions:
            raise ValueError("'UnitManager.__rmod__' function cannot" +
                             " operate on 'UnitManager' types of unequal" +
                             " dimensions.\n{0} != {1}".
                             format(repr(self.dimensions), repr(y.dimensions)))
        return self.clone(y.get() % self.get())

    def __rmul__(self, y):
        new_dim = self.multiply_dimensions(self, y)
        return self.clone(self.get() * y.get(),
                          copy_dim=False,
                          new_dim=new_dim)

    def __rpow__(self, *args):
        raise TypeError("'UnitManager.__rpow__' not implemented because" +
                        " applying arbitrary powers to values with units" +
                        " opens a giant can of worms that really shouldn't" +
                        " be forced on anyone. Please, just say x*x or" +
                        " 1.0/(x*x) etc. for your powers.")

    def __rsub__(self, y):
        if self.dimensions != y.dimensions:
            raise ValueError("'UnitManager.__rsub__' function cannot" +
                             " operate on 'UnitManager' types of unequal" +
                             " dimensions.\n{0} != {1}".
                             format(repr(self.dimensions), repr(y.dimensions)))
        return self.clone(y.get() - self.get())

    def __rtruediv__(self, y):
        return self.clone(y.get() / self.get())

    def __str__(self):
        """
        Return a string representation of the stored value in the current
        unit system
        """
        return str(self.val)

    def __sub__(self, y):
        return self.clone(self.get() - y.get())

    def __truediv__(self, y):
        new_dim = self.divide_dimensions(self, y)
        return self.clone(self.get() / y.get(),
                          copy_dim=False,
                          new_dim=new_dim)

    def __trunc__(self, y):
        return self.clone(self.get().__trunc__())


def unit_tests():
    def unit_test(val, input_units, val_good, output_units, dim):
        msg = ("\nUnit test: {0}".format(dim) +
               "\n    {0} {1} ---> {2} {3}".
               format(val, input_units, val_good, output_units))
        a = UnitManager(val, input_units, dim)
        b = a.get(system=output_units)

        reldiff = abs(b - val_good) / max(abs(b), abs(val_good))
        if reldiff > 1.0e-10:
            msg += "\n            FAIL: got {0} reldiff {1}".format(b, reldiff)
            sys.exit(msg)
        else:
            msg += "\n            PASS: got {0} reldiff {1}".format(b, reldiff)
        return msg + "\n"

    out = ""
    out += unit_test(1.0, "SI", 100.0, "CGSK", "length")
    out += unit_test(1.0, "CGSK", 0.01, "SI", "length")
    out += unit_test(1.0e9, "SI", 1.0, "SESAME", "stress")
    out += unit_test(1.0e9, "SI", 0.01, "SHOCK", "stress")
    if "FAIL" in out:
        sys.exit(out)
    return

if __name__ == "__main__":
    unit_tests()

    def usage():
        msg = ("Example:\n\n"
               "  > ./this_file.py 1.0 si cgsk length\n"
               "  100.0\n\n"
               "Inputs:\n"
               "  > ./this_file.py val input_units output_units dim\n\n" +
               UnitManager.class_info())
        sys.exit(msg)

    if len(sys.argv) != 5:
        usage()

    try:
        val = float(sys.argv[1])
    except ValueError:
        sys.stderr.write("ERROR: Must give a valid float value")
        usage()

    # def convert(cls, value, units, input_unit_system, output_unit_system):
    sys.stderr.write("Converted: {0}".format(
        UnitManager.transform(val, sys.argv[4], sys.argv[2], sys.argv[3])))
