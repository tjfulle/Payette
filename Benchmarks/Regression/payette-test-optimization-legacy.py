#!/usr/bin/env python

from config import *
from Source.Payette_test import PayetteTest

class Test(PayetteTest):

    def __init__(self, check=True):
        super(Test, self).__init__(check)
        self.enabled = True

        self.name = os.path.splitext(os.path.basename(__file__))[0]
        self.tdir = os.path.dirname(os.path.realpath(__file__))

        self.infile = "{0}.inp".format(os.path.join(self.tdir, self.name))
        self.outfile = "{0}.opt/{0}.opt".format(self.name)
        self.baseline = "{0}.gold".format(os.path.join(self.tdir, self.name))
        self.keywords = ["builtin", "medium", "regression", "optimization",
                         "cobyla"]
        self.runcommand = ["payette", "--no-writeprops",
                           self.infile]
        self.material = "elastic"
        self.aux_files = [os.path.join(self.tdir, "optimization_tests.tbl"),
                          os.path.join(self.tdir, "regression_tests.tbl")]

        self.compare_method = self.compare_opt_params

        self.owner = 'Tim Fuller'
        self.date = 'March 30, 2012'
        self.description = """Test of the simplex optimization """

        if check:
            self.check_setup()

        pass


if __name__ == '__main__':
    import time

    test = Test()

    test.runFromTerminal(sys.argv[1:])