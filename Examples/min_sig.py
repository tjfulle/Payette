import os, sys
import numpy as np
import Source.Payette_utils as pu
import Source.Payette_extract as pe

# Do operations on the gold file at the module level so they are only done once
DIR = os.path.dirname(os.path.realpath(__file__))
GOLD_F = os.path.join(DIR, "exmpls.gold")
if not os.path.isfile(GOLD_F):
    pu.report_and_raise_error("{0} not found".format(GOLD_F))

# extract only what we want from the gold and output files
COMP = ["@sig11", "@sig22", "@sig33"]
NC = len(COMP)
XG = np.array(pe.extract([GOLD_F] + COMP, silent=True))


def obj_fn(*args):
    """Evaluates the error between the simulation output and the "gold" answer

    Parameters
    ----------
    args : tuple
        args[0] : output file from simulation

    Returns
    -------
    error : float
        The error between the output and the "gold" answer

    Notes
    -----
    With this objective function, the maximum root mean squared error between
    SIG11, SIG22, and SIG33 from the simulation output and the gold result is
    returned as the error.

    """

    out_f = args[0]

    # extract only what we want from the gold and output files
    xo = np.array(pe.extract([out_f] + COMP, silent=True))

    # do the comparison
    anrmsd = []
    for idx in range(NC):
        rmsd = np.sqrt(np.mean((XG[:, idx] - xo[:, idx]) ** 2))
        dnom = abs(np.amax(xo[:, idx]) - np.amin(xo[:, idx]))
        nrmsd = rmsd / dnom if dnom >= 2.e-16 else rmsd
        anrmsd.append(nrmsd)
        continue

    error = np.amax(np.abs(np.array(anrmsd)))
    return error