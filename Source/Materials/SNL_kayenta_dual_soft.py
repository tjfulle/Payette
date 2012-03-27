#
#    Copyright (2011) Sandia Corporation.
#    Use and export of this program may require a license from
#    the United States Government.
#
import sys
import numpy as np

from Source.Payette_utils import *
from Source.Payette_constitutive_model import ConstitutiveModelPrototype
try:
    import Source.Materials.Library.kayenta_dual_soft as mtllib
    imported = True
except:
    imported = False
    pass

attributes = {
    "payette material":True,
    "name":'kayenta_dual_soft',
    "fortran source":True,
    "build script":os.path.join(PAYETTE_MATERIALS_FORTRAN,
                                "Kayenta_Dual_Soft/build.py"),
    "aliases":[],
    "material type":["special"]
    }

class KayentaDualSoft(ConstitutiveModelPrototype):
    '''
    CLASS NAME
       Kayenta

    PURPOSE
       Constitutive model for a Kayenta material. When instantiated, the Kayenta
       material initializes itself by first checking the user input
       (_check_props) and then initializing any internal state variables
       (_set_field). Then, at each timestep, the driver update the Material state
       by calling updateState.

    METHODS
       _check_props
       _set_field
       updateState

    FORTRAN

       The core code for the Elastic material is contained in
       ./Fortran/Kayenta/kayenta_f77.f. The module Library/kayenta is created by
       f2py. kayenta_f77.f defines the following public subroutines

          kayenta_chk: fortran data check routine called by _check_props
          kayenta_rxv: fortran field initialization  routine called by _set_field
          kayenta_calc: fortran stress update called by updateState

       See the documentation in kayenta_f77.f for more information.

    AUTHORS
       Tim Fuller, Sandia National Laboratories, tjfulle@sandia.gov
    '''
    def __init__(self):
        ConstitutiveModelPrototype.__init__(self)
        self.name = attributes["name"]
        self.aliases = attributes["aliases"]
        self.imported = imported

        nbasicinput = 70
        ib = nbasicinput - 1
        self.registerParameter("B0",0,aliases=['BKMOD'])
        self.registerParameter("B1",1,aliases=[])
        self.registerParameter("B2",2,aliases=[])
        self.registerParameter("B3",3,aliases=[])
        self.registerParameter("B4",4,aliases=[])
        self.registerParameter("G0",5,aliases=['SHMOD'])
        self.registerParameter("G1",6,aliases=[])
        self.registerParameter("G2",7,aliases=[])
        self.registerParameter("G3",8,aliases=[])
        self.registerParameter("G4",9,aliases=[])
        self.registerParameter("RJS",10,aliases=[])
        self.registerParameter("RKS",11,aliases=[])
        self.registerParameter("RKN",12,aliases=[])
        self.registerParameter("A1",13,aliases=['yield strength'])
        self.registerParameter("A2",14,aliases=[])
        self.registerParameter("A3",15,aliases=[])
        self.registerParameter("A4",16,aliases=[])
        self.registerParameter("P0",17,aliases=[])
        self.registerParameter("P1",18,aliases=[])
        self.registerParameter("P2",19,aliases=[])
        self.registerParameter("P3",20,aliases=[])
        self.registerParameter("CR",21,aliases=[])
        self.registerParameter("RK",22,aliases=[])
        self.registerParameter("RN",23,aliases=[])
        self.registerParameter("HC",24,aliases=[])
        self.registerParameter("CTI1",25,aliases=['CUTI1'])
        self.registerParameter("CTPS",26,aliases=['CUTPS'])
        self.registerParameter("T1",27,aliases=[])
        self.registerParameter("T2",28,aliases=[])
        self.registerParameter("T3",29,aliases=[])
        self.registerParameter("T4",30,aliases=[])
        self.registerParameter("T5",31,aliases=[])
        self.registerParameter("T6",32,aliases=[])
        self.registerParameter("T7",33,aliases=[])
        self.registerParameter("J3TYPE",34,aliases=[])
        self.registerParameter("A2PF",35,aliases=[])
        self.registerParameter("A4PF",36,aliases=[])
        self.registerParameter("CRPF",37,aliases=[])
        self.registerParameter("RKPF",38,aliases=[])
        self.registerParameter("SUBX",39,aliases=[])
        self.registerParameter("DEJAVU",40,aliases=[])
        self.registerParameter("FAIL0",41,aliases=['TFAIL'])
        self.registerParameter("FAIL1",42,aliases=['FSPEED'])
        self.registerParameter("FAIL2",43,aliases=[])
        self.registerParameter("FAIL3",44,aliases=[])
        self.registerParameter("FAIL4",45,aliases=[])
        self.registerParameter("FAIL5",46,aliases=[])
        self.registerParameter("FAIL6",47,aliases=[])
        self.registerParameter("FAIL7",48,aliases=[])
        self.registerParameter("FAIL8",49,aliases=[])
        self.registerParameter("FAIL9",50,aliases=[])
        self.registerParameter("PEAKI1I",51,aliases=[])
        self.registerParameter("STRENI",52,aliases=[])
        self.registerParameter("FSLOPEI",53,aliases=[])
        self.registerParameter("PEAKI1F",54,aliases=[])
        self.registerParameter("STRENF",55,aliases=[])
        self.registerParameter("SOFTENING",56,aliases=['JOBFAIL'])
        self.registerParameter("FSLOPEF",57,aliases=[])
        self.registerParameter("FAILSTAT",58,aliases=[])
        self.registerParameter("IEOSID",59,aliases=['EOSID'])
        self.registerParameter("USEHOSTEOS",60,aliases=[])
        self.registerParameter("DILATLIM",61,aliases=[])
        self.registerParameter("FREE1",62,aliases=['FREE01'])
        self.registerParameter("FREE2",63,aliases=['FREE02'])
        self.registerParameter("FREE3",64,aliases=['FREE03'])
        self.registerParameter("FREE4",65,aliases=['FREE04'])
        self.registerParameter("FREE5",66,aliases=['FREE05'])
        self.registerParameter("CTPSF",67,aliases=['CUTPSF'])
        self.registerParameter("YSLOPEI",68,aliases=[])
        self.registerParameter("YSLOPEF",69,aliases=[])
        self.registerParameter("TMPRXP",ib+1,aliases=[])
        self.registerParameter("THERM01",ib+2,aliases=['THERM1'])
        self.registerParameter("THERM02",ib+3,aliases=['THERM2'])
        self.registerParameter("THERM03",ib+4,aliases=['THERM3'])
        self.registerParameter("TMPRM0",ib+5,aliases=['reference melt temperature'])
        self.registerParameter("RHO0",ib+6,aliases=['reference density'])
        self.registerParameter("TMPR0",ib+7,aliases=['reference temperature'])
        self.registerParameter("SNDSP0",ib+8,aliases=['reference soundspeed'])
        self.registerParameter("S1MG",ib+9,aliases=[])
        self.registerParameter("GRPAR",ib+10,aliases=['GRPAR0'])
        self.registerParameter("CV",ib+11,aliases=[])
        self.registerParameter("ESFT",ib+12,aliases=[])
        self.registerParameter("RP",ib+13,aliases=[])
        self.registerParameter("PS",ib+14,aliases=[])
        self.registerParameter("PE",ib+15,aliases=[])
        self.registerParameter("CE",ib+16,aliases=[])
        self.registerParameter("RNSUB",ib+17,aliases=[])
        self.registerParameter("S2MG",ib+18,aliases=[])
        self.registerParameter("TYP",ib+19,aliases=[])
        self.registerParameter("RO",ib+20,aliases=[])
        self.registerParameter("TO",ib+21,aliases=[])
        self.registerParameter("SMG",ib+22,aliases=[])
        self.registerParameter("GRPARO",ib+23,aliases=[])
        self.registerParameter("BMG",ib+24,aliases=[])
        self.registerParameter("XB",ib+25,aliases=[])
        self.registerParameter("RNBMG",ib+26,aliases=[])
        self.registerParameter("RPWR",ib+27,aliases=[])
        self.nprop = len(self.parameter_table.keys())
        self.ndc = 13
        pass

    # Private methods
    def _check_props(self,**kwargs):
        a = [kwargs["props"],kwargs["props"],np.zeros(13),migError,migMessage]
        if not PAYETTE_F2PY_CALLBACK: a = a[:-2]
        return mtllib.kayenta_chk(*a)

    def _set_field(self,*args,**kwargs):
        a = [self.ui,self.ui,self.dc,migError,migMessage]
        if not PAYETTE_F2PY_CALLBACK: a = a[:-2]
        return mtllib.kayenta_rxv(*a)

    # Public Methods
    def setUp(self,payette,props):
        self.dc = np.zeros(self.ndc)
        self.ui0 = np.array(props)
        self.ui,self.dc = self._check_props(props=props)
        (self.ui,self.nsv,namea,keya,self.sv,
         self.rdim,self.iadvct,self.itype) = self._set_field()
        self.namea = parseToken(self.nsv,namea)
        self.keya = parseToken(self.nsv,keya)

        # register the extra variables with the payette object
        payette.registerExtraVariables(self.nsv,self.namea,self.keya,self.sv)

        self.bulk_modulus,self.shear_modulus = self.ui[0],self.ui[5]
        return

    def updateState(self,*args,**kwargs):
        '''
           update the material state based on current state and strain increment
        '''
        dt,d,fold,fnew,efield,sigold,svold = args
        a = [dt,self.ui,self.ui,self.dc,sigold,d,svold,migError,migMessage]
        if not PAYETTE_F2PY_CALLBACK: a = a[:-2]
        signew,svnew,usm = mtllib.kayenta_calc(*a)
        self.sv = np.array(svnew)
        return signew,svnew
