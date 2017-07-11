from pyslalib import slalib as S
import numpy as N
import numpy.testing as T
import math, unittest

#
# Note:  This file is based on the sla_test.f file that is used
#        to test the Fortran version of the code.
#
# Scott M. Ransom <sransom@nrao.edu>, 2007
#

# Copied from https://github.com/scottransom/pyslalib/blob/master/test/test_slalib.py
# stored as run_test.py for automatic test running with conda build
# Edited 2016 by Michael Sarahan for Python 3 string comparison compatibility

# The Fortran code always returns byte strings.  Python 2 is happy with this,
# as it is its default string representation.  Python 3 requires more care.

# The strategy taken here is to force test values that we provide to be
# bytestrings, so that they can be compared with the fortran output.

# None of the numeric code is affected by Python 2 vs Python 3.

def safe_str(obj):
    """ return the byte string representation of obj """
    if hasattr(obj, "encode"):
        obj = obj.encode('unicode_escape')
    return obj

class TestSLALIBFunctions(unittest.TestCase):

    def testaddet(self):
        rm = 2.0
        dm = -1.0
        eq = 1975.0
        r1, d1 = S.sla_addet(rm, dm, eq)
        T.assert_almost_equal(r1 - rm, 2.983864874295250e-6, 12, 'sla_addet, r1')
        T.assert_almost_equal(d1 - dm, 2.379650804185118e-7, 12, 'sla_addet, d1')
        r2, d2 = S.sla_subet(r1, d1, eq)
        T.assert_almost_equal(r2 - rm, 0, 12, 'sla_subet, r2')
        T.assert_almost_equal(d2 - dm, 0, 12, 'sla_subet, d2')

    def testafin(self):
        s = '12 34 56.7 |'
        i = 1
        i, f, j = S.sla_afin(s, i)
        T.assert_equal(i, 12, 'sla_afin, i')
        T.assert_almost_equal(f, 0.2196045986911432, 6, 'sla_afin, a')
        T.assert_equal(j, 0, 'sla_afin, j')
        i = 1
        i, d, j = S.sla_dafin(s, i)
        T.assert_equal(i, 12, 'sla_dafin, i')
        T.assert_almost_equal(d, 0.2196045986911432, 12, 'sla_dafin, a')
        T.assert_equal(j, 0, 'sla_dafin, j')

    def testairmas(self):
        T.assert_almost_equal(S.sla_airmas(1.2354), 3.015698990074724,
                              12, 'sla_airmas')

    def testaltaz(self):
        (az, azd, azdd, el, eld, eldd, pa, pad, padd) = \
             S.sla_altaz (0.7, -0.7, -0.65)
        T.assert_almost_equal(az, 4.400560746660174, 12, 'sla_altaz, az')
        T.assert_almost_equal(azd, -0.2015438937145421, 13, 'sla_altaz, azd')
        T.assert_almost_equal(azdd, -0.4381266949668748, 13, 'sla_altaz, azdd')
        T.assert_almost_equal(el, 1.026646506651396, 12, 'sla_altaz, el')
        T.assert_almost_equal(eld, -0.7576920683826450, 13, 'sla_altaz, eld')
        T.assert_almost_equal(eldd, 0.04922465406857453, 14, 'sla_altaz, eldd')
        T.assert_almost_equal(pa, 1.707639969653937, 12, 'sla_altaz, pa')
        T.assert_almost_equal(pad, 0.4717832355365627, 13, 'sla_altaz, pad')
        T.assert_almost_equal(padd, -0.2957914128185515, 13, 'sla_altaz, padd')

    def testamp(self):
        rm, dm = S.sla_amp(2.345, -1.234, 50100.0, 1990.0)
        T.assert_almost_equal(rm, 2.344472180027961, 11, 'sla_amp, r')
        T.assert_almost_equal(dm, -1.233573099847705, 11, 'sla_amp, d')

    def testaop(self):
        ds2r = 7.2722052166430399038487115353692196393452995355905e-5
        dap = -0.1234
        date = 51000.1
        dut = 25.0
        elongm = 2.1
        phim = 0.5
        hm = 3000.0
        xp = -0.5e-6
        yp = 1e-6
        tdk = 280.0
        pmb = 550.0
        rh = 0.6
        tlr = 0.006
        for i in [1,2,3]:
            if i==1:
                rap = 2.7
                wl = 0.45
            elif i==2:
                rap = 2.345
            else:
                wl = 1e6
            aob, zob, hob, dob, rob = S.sla_aop(rap, dap, date, dut,
                                                elongm, phim, hm, xp, yp,
                                                tdk, pmb, rh, wl, tlr)
            if i==1:
                T.assert_almost_equal(aob, 1.812817787123283034, 10, 'sla_aop, lo aob')
                T.assert_almost_equal(zob, 1.393860816635714034, 10, 'sla_aop, lo zob')
                T.assert_almost_equal(hob, -1.297808009092456683, 10, 'sla_aop, lo hob')
                T.assert_almost_equal(dob, -0.122967060534561, 10, 'sla_aop, lo dob')
                T.assert_almost_equal(rob, 2.699270287872084, 10, 'sla_aop, lo rob')
            elif i==2:
                T.assert_almost_equal(aob, 2.019928026670621442, 10, 'sla_aop, aob/o')
                T.assert_almost_equal(zob, 1.101316172427482466, 10, 'sla_aop, zob/o')
                T.assert_almost_equal(hob, -0.9432923558497740862, 10, 'sla_aop, hob/o')
                T.assert_almost_equal(dob, -0.1232144708194224, 10, 'sla_aop, dob/o')
                T.assert_almost_equal(rob, 2.344754634629428, 10, 'sla_aop, rob/o')
            else:
                T.assert_almost_equal(aob, 2.019928026670621442, 10, 'sla_aop, aob/r')
                T.assert_almost_equal(zob, 1.101267532198003760, 10, 'sla_aop, zob/r')
                T.assert_almost_equal(hob, -0.9432533138143315937, 10, 'sla_aop, hob/r')
                T.assert_almost_equal(dob, -0.1231850665614878, 10, 'sla_aop, dob/r')
                T.assert_almost_equal(rob, 2.344715592593984, 10, 'sla_aop, rob/r')
        date = 48000.3
        wl = 0.45
        aoprms = S.sla_aoppa(date, dut, elongm, phim, hm, xp, yp, tdk, pmb, rh, wl, tlr)
        T.assert_almost_equal(aoprms[0], 0.4999993892136306, 13, 'sla_aoppa, 1')
        T.assert_almost_equal(aoprms[1], 0.4794250025886467, 13, 'sla_aoppa, 2')
        T.assert_almost_equal(aoprms[2], 0.8775828547167932, 13, 'sla_aoppa, 3')
        T.assert_almost_equal(aoprms[3], 1.363180872136126e-6, 13, 'sla_aoppa, 4')
        T.assert_almost_equal(aoprms[4], 3000.0, 10, 'sla_aoppa, 5')
        T.assert_almost_equal(aoprms[5], 280.0, 11, 'sla_aoppa, 6')
        T.assert_almost_equal(aoprms[6], 550.0, 11, 'sla_aoppa, 7')
        T.assert_almost_equal(aoprms[7], 0.6, 13, 'sla_aoppa, 8')
        T.assert_almost_equal(aoprms[8], 0.45, 13, 'sla_aoppa, 9')
        T.assert_almost_equal(aoprms[9], 0.006, 15, 'sla_aoppa, 10')
        T.assert_almost_equal(aoprms[10], 0.0001562803328459898, 13, 'sla_aoppa, 11')
        T.assert_almost_equal(aoprms[11], -1.792293660141e-7, 13, 'sla_aoppa, 12')
        T.assert_almost_equal(aoprms[12], 2.101874231495843, 13, 'sla_aoppa, 13')
        T.assert_almost_equal(aoprms[13], 7.601916802079765, 8, 'sla_aoppa, 14')
        rap, dap = S.sla_oap('r', 1.6, -1.01, date, dut, elongm, phim,
                             hm, xp, yp, tdk, pmb, rh, wl, tlr)
        T.assert_almost_equal(rap, 1.601197569844787, 10, 'sla_oap, rr')
        T.assert_almost_equal(dap, -1.012528566544262, 10, 'sla_oap, rd')
        rap, dap = S.sla_oap('h', -1.234, 2.34, date, dut, elongm, phim,
                             hm, xp, yp, tdk, pmb, rh, wl, tlr)
        T.assert_almost_equal(rap, 5.693087688154886463, 10, 'sla_oap, hr')
        T.assert_almost_equal(dap, 0.8010281167405444, 10, 'sla_oap, hd')
        rap, dap = S.sla_oap('a', 6.1, 1.1, date, dut, elongm, phim,
                             hm, xp, yp, tdk, pmb, rh, wl, tlr)
        T.assert_almost_equal(rap, 5.894305175192448940, 10, 'sla_oap, ar')
        T.assert_almost_equal(dap, 1.406150707974922, 10, 'sla_oap, ad')
        rap, dap = S.sla_oapqk('r', 2.1, -0.345, aoprms)
        T.assert_almost_equal(rap, 2.10023962776202, 10, 'sla_oapqk, rr')
        T.assert_almost_equal(dap, -0.3452428692888919, 10, 'sla_oapqk, rd')
        rap, dap = S.sla_oapqk('h', -0.01, 1.03, aoprms)
        T.assert_almost_equal(rap, 1.328731933634564995, 10, 'sla_oapqk, hr')
        T.assert_almost_equal(dap, 1.030091538647746, 10, 'sla_oapqk, hd')
        rap, dap = S.sla_oapqk('a', 4.321, 0.987, aoprms)
        T.assert_almost_equal(rap, 0.4375507112075065923, 10, 'sla_oapqk, ar')
        T.assert_almost_equal(dap, -0.01520898480744436, 10, 'sla_oapqk, ad')
        S.sla_aoppat(date + ds2r, aoprms)
        T.assert_almost_equal(aoprms[13], 7.602374979243502, 8, 'sla_aoppat')

    def testbear(self):
        a1 = 1.234
        b1 = -0.123
        a2 = 2.345
        b2 = 0.789
        T.assert_almost_equal(S.sla_bear(a1, b1, a2, b2),
                              0.7045970341781791, 6, 'sla_bear')
        T.assert_almost_equal(S.sla_dbear(a1, b1, a2, b2),
                              0.7045970341781791, 12, 'sla_dbear')
        d1 = S.sla_dcs2c(a1, b1)
        d2 = S.sla_dcs2c(a2, b2)
        T.assert_almost_equal(S.sla_pav(d1, d2), 0.7045970341781791,
                              6, 'sla_pav')
        T.assert_almost_equal(S.sla_dpav(d1, d2), 0.7045970341781791,
                              12, 'sla_dpav')

    def testcaf2r(self):
        r, j = S.sla_caf2r(76, 54, 32.1)
        T.assert_almost_equal(r, 1.342313819975276, 6, 'sla_caf2r, r')
        T.assert_equal(j, 0, 'sla_caf2r, j')
        dr, j = S.sla_daf2r (76, 54, 32.1)
        T.assert_almost_equal(dr, 1.342313819975276, 12, 'sla_daf2r, r')
        T.assert_equal(j, 0, 'sla_caf2r, j')

    def testcaldj(self):
        djm, j = S.sla_caldj(1999, 12, 31)
        T.assert_almost_equal(djm, 51543.0, 15, 'sla_caldj')

    def testcalyd(self):
        ny, nd, j = S.sla_calyd(46, 4, 30)
        T.assert_equal(ny, 2046, 'sla_calyd, y')
        T.assert_equal(nd, 120, 'sla_calyd, d')
        T.assert_equal(j, 0, 'sla_calyd, j')
        ny, nd, j = S.sla_clyd (-5000, 1, 1)
        T.assert_equal(j, 1, 'sla_clyd, illegal year')
        ny, nd, j = S.sla_clyd (1900, 0, 1)
        T.assert_equal(j, 2, 'sla_clyd, illegal month')
        ny, nd, j = S.sla_clyd (1900, 2, 29)
        T.assert_equal(ny, 1900, 'sla_clyd, illegal day (y)')
        T.assert_equal(nd, 61, 'sla_clyd, illegal day (d)')
        T.assert_equal(j, 3, 'sla_clyd, illegal day (j)')
        ny, nd, j = S.sla_clyd(2000, 2, 29)
        T.assert_equal(ny, 2000, 'sla_clyd, y')
        T.assert_equal(nd, 60, 'sla_clyd, d')
        T.assert_equal(j, 0, 'sla_clyd, j')

    def testcc2s(self):
        v = N.asarray([100.0, -50.0, 25.0])
        a, b = S.sla_cc2s(v)
        T.assert_almost_equal(a, -0.4636476090008061, 6, 'sla_cc2s, a')
        T.assert_almost_equal(b, 0.2199879773954594, 6, 'sla_cc2s, b')
        da, db = S.sla_dcc2s (v)
        T.assert_almost_equal(da, -0.4636476090008061, 12, 'sla_dcc2s, a')
        T.assert_almost_equal(db, 0.2199879773954594, 12, 'sla_dcc2s, b')

    def testcc62s(self):
        v = N.asarray([100.0, -50.0, 25.0, -0.1, 0.2, 0.7])
        a, b, r, ad, bd, rd = S.sla_cc62s(v)
        T.assert_almost_equal(a, -0.4636476090008061, 6, 'sla_cc62s, a')
        T.assert_almost_equal(b, 0.2199879773954594, 6, 'sla_cc62s, b')
        T.assert_almost_equal(r, 114.564392373896, 3, 'sla_cc62s, r')
        T.assert_almost_equal(ad, 0.001200000000000000, 9, 'sla_cc62s, ad')
        T.assert_almost_equal(bd, 0.006303582107999407, 8, 'sla_cc62s, bd')
        T.assert_almost_equal(rd, -0.02182178902359925, 7, 'sla_cc62s, rd')
        da, db, dr, dad, dbd, drd = S.sla_dc62s(v)
        T.assert_almost_equal(da, -0.4636476090008061, 6, 'sla_dc62s, a')
        T.assert_almost_equal(db, 0.2199879773954594, 6, 'sla_dc62s, b')
        T.assert_almost_equal(dr, 114.564392373896, 9, 'sla_dc62s, r')
        T.assert_almost_equal(dad, 0.001200000000000000, 15, 'sla_dc62s, ad')
        T.assert_almost_equal(dbd, 0.006303582107999407, 14, 'sla_dc62s, bd')
        T.assert_almost_equal(drd, -0.02182178902359925, 13, 'sla_dc62s, rd')

    def testcd2tf(self):
        s, ihmsf = S.sla_cd2tf(4, -0.987654321)
        T.assert_equal(s, safe_str('-'), 'sla_cd2tf, s')
        T.assert_equal(ihmsf[0], 23, 'sla_cd2tf, (1)')
        T.assert_equal(ihmsf[1], 42, 'sla_cd2tf, (2)')
        T.assert_equal(ihmsf[2], 13, 'sla_cd2tf, (3)')
        T.assert_almost_equal(ihmsf[3], 3333, -3, 'sla_cd2tf, (4)')
        s, ihmsf = S.sla_dd2tf(4, -0.987654321)
        T.assert_equal(s, safe_str('-'), 'sla_dd2tf, s')
        T.assert_equal(ihmsf[0], 23, 'sla_dd2tf, (1)')
        T.assert_equal(ihmsf[1], 42, 'sla_dd2tf, (2)')
        T.assert_equal(ihmsf[2], 13, 'sla_dd2tf, (3)')
        T.assert_equal(ihmsf[3], 3333, 'sla_dd2tf, (4)')

    def testcldj(self):
        d, j = S.sla_cldj(1899, 12, 31)
        T.assert_almost_equal(d, 15019.0, 15, 'sla_cldj, d')
        T.assert_equal(j, 0, 'sla_cldj, j')

    def testcr2af(self):
        s, idmsf = S.sla_cr2af(4, 2.345)
        T.assert_equal(s, safe_str('+'), 'sla_cr2af, s')
        T.assert_equal(idmsf[0], 134, 'sla_cr2af, (1)')
        T.assert_equal(idmsf[1], 21, 'sla_cr2af, (2)')
        T.assert_equal(idmsf[2], 30, 'sla_cr2af, (3)')
        T.assert_almost_equal(idmsf[3], 9706, -3, 'sla_cr2af, (4)')
        s, idmsf = S.sla_dr2af(4, 2.345)
        T.assert_equal(s, safe_str('+'), 'sla_dr2af, s')
        T.assert_equal(idmsf[0], 134, 'sla_dr2af, (1)')
        T.assert_equal(idmsf[1], 21, 'sla_dr2af, (2)')
        T.assert_equal(idmsf[2], 30, 'sla_dr2af, (3)')
        T.assert_equal(idmsf[3], 9706, 'sla_dr2af, (4)')

    def testcr2tf(self):
        s, ihmsf = S.sla_cr2tf(4, -3.01234)
        T.assert_equal(s, safe_str('-'), 'sla_cr2tf, s')
        T.assert_equal(ihmsf[0], 11, 'sla_cr2tf, (1)')
        T.assert_equal(ihmsf[1], 30, 'sla_cr2tf, (2)')
        T.assert_equal(ihmsf[2], 22, 'sla_cr2tf, (3)')
        T.assert_almost_equal(ihmsf[3], 6484, -3, 'sla_cr2tf, (4)')
        s, ihmsf = S.sla_dr2tf(4, -3.01234)
        T.assert_equal(s, safe_str('-'), 'sla_dr2tf, s')
        T.assert_equal(ihmsf[0], 11, 'sla_dr2tf, (1)')
        T.assert_equal(ihmsf[1], 30, 'sla_dr2tf, (2)')
        T.assert_equal(ihmsf[2], 22, 'sla_dr2tf, (3)')
        T.assert_equal(ihmsf[3], 6484, 'sla_dr2tf, (4)')

    def testcs2c6(self):
        v = S.sla_cs2c6(-3.21, 0.123, 0.456,
                        -7.8e-6, 9.01e-6, -1.23e-5)
        ans = N.asarray([-0.4514964673880165, 0.03093394277342585,
                         0.05594668105108779, 1.292270850663260e-5,
                         2.652814182060692e-6, 2.568431853930293e-6])
        T.assert_array_almost_equal(v, ans, 6, 'sla_cs2c6')
        dv = S.sla_ds2c6(-3.21, 0.123, 0.456,
                         -7.8e-6, 9.01e-6, -1.23e-5)
        T.assert_array_almost_equal(dv, ans, 12, 'sla_ds2c6')

    def testctf2d(self):
        d, j = S.sla_ctf2d (23, 56, 59.1e0)
        T.assert_almost_equal(d, 0.99790625, 6, 'sla_ctf2d, d')
        T.assert_equal(j, 0, 'sla_ctf2d, j')
        dd, j = S.sla_dtf2d(23, 56, 59.1)
        T.assert_almost_equal(dd, 0.99790625, 12, 'sla_dtf2d, d')
        T.assert_equal(j, 0, 'sla_dtf2d, j')

    def testctf2r(self):
        r, j = S.sla_ctf2r(23, 56, 59.1)
        T.assert_almost_equal(r, 6.270029887942679, 6, 'sla_ctf2r, r')
        T.assert_equal(j, 0, 'sla_ctf2r, j')
        dr, j = S.sla_dtf2r (23, 56, 59.1)
        T.assert_almost_equal(dr, 6.270029887942679, 12, 'sla_dtf2r, r')
        T.assert_equal(j, 0, 'sla_dtf2r, j')

    def testdat(self):
        T.assert_almost_equal(S.sla_dat(43900), 18, 0, 'sla_dat')
        T.assert_almost_equal(S.sla_dtt(40404), 39.709746, 12, 'sla_dtt')
        T.assert_almost_equal(S.sla_dt(500), 4686.7, 10, 'sla_dt, 500')
        T.assert_almost_equal(S.sla_dt(1400), 408, 11, 'sla_dt, 1400')
        T.assert_almost_equal(S.sla_dt(1950), 27.99145626, 12, 'sla_dt, 1950')

    def testdbjin(self):
        s = '  b1950, , j 2000, b1975 je     '
        i = 1
        i, d, ja, jb = S.sla_dbjin(s, i)
        T.assert_equal(i, 9, 'sla_dbjin, i1')
        T.assert_almost_equal(d, 1950, 15, 'sla_dbjin, d1')
        T.assert_equal(ja, 0, 'sla_dbjin, ja1')
        T.assert_equal(jb, 1, 'sla_dbjin, jb1')
        i, d, ja, jb = S.sla_dbjin(s, i)
        T.assert_equal(i, 11, 'sla_dbjin, i2')
        # this is different than in slalib_test.f since 'd'
        # is output only and the value doesn't pass through
        T.assert_almost_equal(d, 0.0, 15, 'sla_dbjin, d2')
        T.assert_equal(ja, 1, 'sla_dbjin, ja2')
        T.assert_equal(jb, 0, 'sla_dbjin, jb2')
        i, d, ja, jb = S.sla_dbjin(s, i)
        T.assert_equal(i, 19, 'sla_dbjin, i3')
        T.assert_almost_equal(d, 2000, 15, 'sla_dbjin, d3')
        T.assert_equal(ja, 0, 'sla_dbjin, ja3')
        T.assert_equal(jb, 2, 'sla_dbjin, jb3')
        i, d, ja, jb = S.sla_dbjin(s, i)
        T.assert_equal(i, 26, 'sla_dbjin, i4')
        T.assert_almost_equal(d, 1975, 15, 'sla_dbjin, d4')
        T.assert_equal(ja, 0, 'sla_dbjin, ja4')
        T.assert_equal(jb, 1, 'sla_dbjin, jb4')
        i, d, ja, jb = S.sla_dbjin(s, i)
        T.assert_equal(i, 26, 'sla_dbjin, i5')
        # this is different than in slalib_test.f since 'd'
        # is output only and the value doesn't pass through
        T.assert_almost_equal(d, 0.0, 15, 'sla_dbjin, d5')
        T.assert_equal(ja, 1, 'sla_dbjin, ja5')
        T.assert_equal(jb, 0, 'sla_dbjin, jb5')

    def testdjcal(self):
        djm = 50123.9999
        iydmf, j = S.sla_djcal(4, djm)
        T.assert_equal(iydmf[0], 1996, 'sla_djcal, y')
        T.assert_equal(iydmf[1], 2, 'sla_djcal, m')
        T.assert_equal(iydmf[2], 10, 'sla_djcal, d')
        T.assert_equal(iydmf[3], 9999, 'sla_djcal, f')
        T.assert_equal(j, 0, 'sla_djcal, j')
        iy, im, id, f, j = S.sla_djcl(djm)
        T.assert_equal(iy, 1996, 'sla_djcl, y')
        T.assert_equal(im, 2, 'sla_djcl, m')
        T.assert_equal(id, 10, 'sla_djcl, d')
        T.assert_almost_equal(f, 0.9999, 7, 'sla_djcl, f')
        T.assert_equal(j, 0, 'sla_djcl, j')

    def testdmat(self):
        da = N.asarray([[2.22,     1.6578,     1.380522],
                        [1.6578,   1.380522,   1.22548578],
                        [1.380522, 1.22548578, 1.1356276122]])
        dv = N.asarray([2.28625, 1.7128825, 1.429432225])
        da, dv, dd, j, iw = S.sla_dmat(da, dv, N.empty(3.0))
        ans = N.asarray([[18.02550629769198, -52.16386644917280607, 34.37875949717850495],
                         [-52.16386644917280607, 168.1778099099805627, -118.0722869694232670],
                         [34.37875949717850495, -118.0722869694232670, 86.50307003740151262]])
        T.assert_array_almost_equal(da, ans, 10, 'sla_dmat, a(3,3)')
        ans = N.asarray([1.002346480763383, 0.03285594016974583489, 0.004760688414885247309])
        T.assert_array_almost_equal(dv, ans, 12, 'sla_dmat, v(3)')
        T.assert_almost_equal(dd, 0.003658344147359863, 12, 'sla_dmat, d')
        T.assert_equal(j, 0, 'sla_dmat, j')

    def teste2h(self):
        dh = -0.3
        dd = -1.1
        dp = -0.7
        da, de = S.sla_de2h(dh, dd, dp)
        T.assert_almost_equal(da, 2.820087515852369, 12, 'sla_de2h, az')
        T.assert_almost_equal(de, 1.132711866443304, 12, 'sla_de2h, el')
        a, e = S.sla_e2h(dh, dd, dp)
        T.assert_almost_equal(a, 2.820087515852369, 6, 'sla_e2h, az')
        T.assert_almost_equal(e, 1.132711866443304, 6, 'sla_e2h, el')
        dh, dd = S.sla_dh2e(da, de, dp)
        T.assert_almost_equal(dh, -0.3, 12, 'sla_dh2e, ha')
        T.assert_almost_equal(dd, -1.1, 12, 'sla_dh2e, dec')
        h, d = S.sla_h2e(da, de, dp)
        T.assert_almost_equal(h, -0.3, 6, 'sla_h2e, ha')
        T.assert_almost_equal(d, -1.1, 6, 'sla_h2e, dec')

    def testearth(self):
        pv = S.sla_earth(1978, 174, 0.87)
        T.assert_almost_equal(pv[0],  3.590867086e-2, 6, 'sla_earth, pv(1)')
        T.assert_almost_equal(pv[1], -9.319285116e-1, 6, 'sla_earth, pv(2)')
        T.assert_almost_equal(pv[2], -4.041039435e-1, 6, 'sla_earth, pv(3)')
        T.assert_almost_equal(pv[3], 1.956930055e-7, 13, 'sla_earth, pv(4)')
        T.assert_almost_equal(pv[4], 5.743797400e-9, 13, 'sla_earth, pv(5)')
        T.assert_almost_equal(pv[5], 2.512001677e-9, 13, 'sla_earth, pv(6)')

    def testecleq(self):
        r, d = S.sla_ecleq(1.234, -0.123, 43210)
        T.assert_almost_equal(r, 1.229910118208851, 12, 'sla_ecleq, ra')
        T.assert_almost_equal(d, 0.2638461400411088, 12, 'sla_ecleq, dec')

    def testecmat(self):
        rm = S.sla_ecmat(41234)
        ans = N.asarray([[1.0, 0.0, 0.0],
                         [0.0, 0.917456575085716, 0.397835937079581],
                         [0.0, -0.397835937079581, 0.917456575085716]])
        T.assert_array_almost_equal(rm, ans, 12, 'sla_ecmat')

    def testecor(self):
        rv, tl = S.sla_ecor(2.345, -0.567, 1995, 306, 0.037)
        T.assert_almost_equal(rv, -19.182460, 3, 'sla_ecor, rv')
        T.assert_almost_equal(tl, -120.36632, 2, 'sla_ecor, tl')

    def testeg50(self):
        dl, db = S.sla_eg50(3.012, 1.234)
        T.assert_almost_equal(dl, 2.305557953813397, 12, 'sla_eg50, l')
        T.assert_almost_equal(db, 0.7903600886585871, 12, 'sla_eg50, b')

    def testepb(self):
        T.assert_almost_equal(S.sla_epb(45123), 1982.419793168669,
                              8, 'sla_epb')

    def testepb2d(self):
        T.assert_almost_equal(S.sla_epb2d(1975.5), 42595.5995279655,
                              7, 'sla_epb2d')

    def testepco(self):
        T.assert_almost_equal(S.sla_epco('b', 'j', 2000),
                              2000.001277513665, 7, 'sla_epco, bj')
        T.assert_almost_equal(S.sla_epco('j', 'b', 1950),
                              1949.999790442300, 7, 'sla_epco, jb')
        T.assert_almost_equal(S.sla_epco('j', 'j', 2000),
                              2000, 7, 'sla_epco, jj')

    def testepj(self):
        T.assert_almost_equal(S.sla_epj(42999), 1976.603696098563,
                              7, 'sla_epj')

    def testepj2d(self):
        T.assert_almost_equal(S.sla_epj2d(2010.077), 55225.124250,
                              6, 'sla_epj2d')

    def testeqecl(self):
        dl, db = S.sla_eqecl(0.789, -0.123, 46555)
        T.assert_almost_equal(dl, 0.7036566430349022, 12, 'sla_eqecl, l')
        T.assert_almost_equal(db, -0.4036047164116848, 12, 'sla_eqecl, b')

    def testeqeqx(self):
        T.assert_almost_equal(S.sla_eqeqx(41234), 5.376047445838358596e-5,
                              17, 'sla_eqeqx')

    def testeqgal(self):
        dl, db = S.sla_eqgal(5.67, -1.23)
        T.assert_almost_equal(dl, 5.612270780904526, 12, 'sla_eqgal, dl')
        T.assert_almost_equal(db, -0.6800521449061520, 12, 'sla_eqgal, db')

    def testetrms(self):
        ev = S.sla_etrms(1976.9)
        ans = N.asarray([-1.621617102537041e-6,
                         -3.310070088507914e-7,
                         -1.435296627515719e-7])
        T.assert_array_almost_equal(ev, ans, 18, 'sla_etrms')

    def testevp(self):
        dvb, dpb, dvh, dph = S.sla_evp(50100, 1990)
        ans1 = N.asarray([-1.807210068604058436e-7,
                          -8.385891022440320e-8,
                          -3.635846882638055e-8])
        T.assert_array_almost_equal(dvb, ans1, 14, 'sla_evp, dvb')
        ans2 = N.asarray([-0.4515615297360333,
                          0.8103788166239596,
                          0.3514505204144827])
        T.assert_array_almost_equal(dpb, ans2, 7, 'sla_evp, dpb')
        ans3 = N.asarray([-1.806354061156890855e-7,
                          -8.383798678086174e-8,
                          -3.635185843644782e-8])
        T.assert_array_almost_equal(dvh, ans3, 14, 'sla_evp, dvh')
        ans4 = N.asarray([-0.4478571659918565,
                          0.8036439916076232,
                          0.3484298459102053])
        T.assert_array_almost_equal(dph, ans4, 7, 'sla_evp, dph')
        dph, dvh, dpb, dvb = S.sla_epv(53411.52501161)
        ans1 = N.asarray([-0.7757238809297653,
                          +0.5598052241363390,
                          +0.2426998466481708])
        T.assert_array_almost_equal(dph, ans1, 12, 'sla_epv, dph')
        ans2 = N.asarray([-0.0109189182414732,
                          -0.0124718726844084,
                          -0.0054075694180650])
        T.assert_array_almost_equal(dvh, ans2, 12, 'sla_epv, dvh')
        ans3 = N.asarray([-0.7714104440491060,
                          +0.5598412061824225,
                          +0.2425996277722475])
        T.assert_array_almost_equal(dpb, ans3, 12, 'sla_epv, dpb')
        ans4 = N.asarray([-0.0109187426811683,
                          -0.0124652546173285,
                          -0.0054047731809662])
        T.assert_array_almost_equal(dvb, ans4, 12, 'sla_epv, dvb')

    def testfitxy(self):
        xye = N.asarray([-23.4, -12.1,     32,  -15.3,
                          10.9,  23.7,     -3,   16.1,
                            45,  32.5,    8.6,    -17,
                          15.3,    10,  121.7,   -3.8])
        # The reshaping is necessary due to C/Fortran order
        xye = N.reshape(xye, (2,8), order='Fortran')
        xym = N.asarray([-23.41,  12.12,  32.03,  15.34,
                          10.93, -23.72,  -3.01, -16.10,
                          44.90, -32.46,   8.55,  17.02,
                          15.31, -10.07, 120.92,   3.81])
        # The reshaping is necessary due to C/Fortran order
        xym = N.reshape(xym, (2,8), order='Fortran')
        coeffs, j = S.sla_fitxy(4, xye, xym)
        ans1 = N.asarray([-7.938263381515947e-3, 1.004640925187200,
                          3.976948048238268e-4, -2.501031681585021e-2,
                          3.976948048238268e-4, -1.004640925187200])
        T.assert_array_almost_equal(coeffs, ans1, 12, 'sla_fitxy, 4/coeffs')
        T.assert_equal(j, 0, 'sla_fitxy, 4/j')
        coeffs, j = S.sla_fitxy(6, xye, xym)
        ans2 = N.asarray([-2.617232551841476e-2, 1.005634905041421,
                          2.133045023329208e-3, 3.846993364417779909e-3,
                          1.301671386431460e-4, -0.9994827065693964])
        T.assert_array_almost_equal(coeffs, ans2, 12, 'sla_fitxy, 6/coeffs')
        T.assert_equal(j, 0, 'sla_fitxy, 6/j')
        xyp, xrms, yrms, rrms = S.sla_pxy(xye, xym, coeffs)
        ans3 = N.asarray([-23.542232946855340, -12.11293062297230597,
                          32.217034593616180, -15.324048471959370,
                          10.914821358630950, 23.712999520015880,
                          -3.087475414568693, 16.09512676604438414,
                          45.05759626938414666, 32.45290015313210889,
                          8.608310538882801, -17.006235743411300,
                          15.348618307280820, 10.07063070741086835,
                          121.5833272936291482, -3.788442308260240])
        # And another reshaping...
        ans3 = N.reshape(ans3, (2,8), order='Fortran')
        T.assert_array_almost_equal(xyp, ans3, 12, 'sla_fitxy, xyp')
        T.assert_almost_equal(xrms ,0.1087247110488075, 13, 'sla_pxy, xrms')
        T.assert_almost_equal(yrms, 0.03224481175794666, 13, 'sla_pxy, yrms')
        T.assert_almost_equal(rrms, 0.1134054261398109, 13, 'sla_pxy, rrms')
        bkwds, j = S.sla_invf(coeffs)
        ans4 = N.asarray([0.02601750208015891, 0.9943963945040283,
                          0.002122190075497872, 0.003852372795357474353,
                          0.0001295047252932767, -1.000517284779212])
        T.assert_array_almost_equal(bkwds, ans4, 12, 'sla_invf, 6')
        T.assert_equal(j, 0, 'sla_invf, j')
        x2, y2 = S.sla_xy2xy(44.5, 32.5, coeffs)
        T.assert_almost_equal(x2,  44.793904912083030, 11, 'sla_xy2xy, x')
        T.assert_almost_equal(y2, -32.473548532471330, 11, 'sla_xy2xy, y')
        xz, yz, xs, ys, perp, orient = S.sla_dcmpf(coeffs)
        T.assert_almost_equal(xz, -0.0260175020801628646, 12, 'sla_dcmpf, xz')
        T.assert_almost_equal(yz, -0.003852372795357474353, 12, 'sla_dcmpf, yz')
        T.assert_almost_equal(xs, -1.00563491346569, 12, 'sla_dcmpf, xs')
        T.assert_almost_equal(ys, 0.999484982684761, 12, 'sla_dcmpf, ys')
        T.assert_almost_equal(perp,-0.002004707996156263, 12, 'sla_dcmpf, p')
        T.assert_almost_equal(orient, 3.14046086182333, 12, 'sla_dcmpf, o')

    def testfk425(self):
        r2000, d2000, dr2000, dd2000, p2000, v2000 = \
               S.sla_fk425(1.234, -0.123, -1e-5, 2e-6, 0.5, 20)
        T.assert_almost_equal(r2000, 1.244117554618727, 12, 'sla_fk425, r')
        T.assert_almost_equal(d2000, -0.1213164254458709, 12, 'sla_fk425, d')
        T.assert_almost_equal(dr2000, -9.964265838268711e-6, 17, 'sla_fk425, dr')
        T.assert_almost_equal(dd2000, 2.038065265773541e-6, 17, 'sla_fk425, dd')
        T.assert_almost_equal(p2000, 0.4997443812415410, 12, 'sla_fk425, p')
        T.assert_almost_equal(v2000, 20.010460915421010, 11, 'sla_fk425, v')

    def testfk45z(self):
        r2000, d2000 = S.sla_fk45z(1.234, -0.123, 1984)
        T.assert_almost_equal(r2000, 1.244616510731691, 12, 'sla_fk45z, r')
        T.assert_almost_equal(d2000, -0.1214185839586555, 12, 'sla_fk45z, d')

    def testfk524(self):
        r1950, d1950, dr1950, dd1950, p1950, v1950 = \
               S.sla_fk524(4.567, -1.23, -3e-5, 8e-6, 0.29, -35)
        T.assert_almost_equal(r1950, 4.543778603272084, 12, 'sla_fk524, r')
        T.assert_almost_equal(d1950, -1.229642790187574, 12, 'sla_fk524, d')
        T.assert_almost_equal(dr1950, -2.957873121769244e-5, 17, 'sla_fk524, dr')
        T.assert_almost_equal(dd1950, 8.117725309659079e-6, 17, 'sla_fk524, dd')
        T.assert_almost_equal(p1950, 0.2898494999992917, 12, 'sla_fk524, p')
        T.assert_almost_equal(v1950, -35.026862824252680, 11, 'sla_fk524, v')

    def testfk52h(self):
        rh, dh, drh, ddh = S.sla_fk52h(1.234, -0.987, 1e-6, -2e-6)
        T.assert_almost_equal(rh, 1.234000000272122558, 13, 'sla_fk52h, r')
        T.assert_almost_equal(dh, -0.9869999235218543959, 13, 'sla_fk52h, d')
        T.assert_almost_equal(drh, 0.000000993178295, 13, 'sla_fk52h, dr')
        T.assert_almost_equal(ddh, -0.000001997665915, 13, 'sla_fk52h, dd')
        r5, d5, dr5, dd5 = S.sla_h2fk5 (rh, dh, drh, ddh)
        T.assert_almost_equal(r5, 1.234, 13, 'sla_h2fk5, r')
        T.assert_almost_equal(d5, -0.987, 13, 'sla_h2fk5, d')
        T.assert_almost_equal(dr5, 1e-6, 13, 'sla_h2fk5, dr')
        T.assert_almost_equal(dd5, -2e-6, 13, 'sla_h2fk5, dd')
        rh, dh = S.sla_fk5hz (1.234, -0.987, 1980)
        T.assert_almost_equal(rh, 1.234000136713611301, 13, 'sla_fk5hz, r')
        T.assert_almost_equal(dh, -0.9869999702020807601, 13, 'sla_fk5hz, d')
        r5, d5, dr5, dd5 = S.sla_hfk5z(rh, dh, 1980)
        T.assert_almost_equal(r5, 1.234, 13, 'sla_hfk5z, r')
        T.assert_almost_equal(d5, -0.987, 13, 'sla_hfk5z, d')
        T.assert_almost_equal(dr5, 0.000000006822074, 13, 'sla_hfk5z, dr')
        T.assert_almost_equal(dd5, -0.000000002334012, 13, 'sla_hfk5z, dd')

    def testfk54z(self):
        r1950, d1950, dr1950, dd1950 = S.sla_fk54z(0.001, -1.55, 1900)
        T.assert_almost_equal(r1950, 6.271585543439484, 12, 'sla_fk54z, r')
        T.assert_almost_equal(d1950, -1.554861715330319, 12, 'sla_fk54z, d')
        T.assert_almost_equal(dr1950, -4.175410876044916011e-8, 20, 'sla_fk54z, dr')
        T.assert_almost_equal(dd1950, 2.118595098308522e-8, 20, 'sla_fk54z, dd')

    def testflotin(self):
        s = '  12.345, , -0 1e3-4 2000  e     '
        i = 1
        fv = 0.0
        i, fv, j = S.sla_flotin(s, i)
        T.assert_equal(i, 10, 'sla_flotin, v5')
        T.assert_almost_equal(fv, 12.345, 5, 'sla_flotin, v1')
        T.assert_equal(j, 0, 'sla_flotin, j1')
        i, fv, j = S.sla_flotin(s, i)
        T.assert_equal(i, 12, 'sla_flotin, i2')
        # this is different than in slalib_test.f since 'fv'
        # is output only and the value doesn't pass through
        T.assert_almost_equal(fv, 0.0, 15, 'sla_flotin, v2')
        T.assert_equal(j, 1, 'sla_flotin, j2')
        i, fv, j = S.sla_flotin(s, i)
        T.assert_equal(i, 16, 'sla_flotin, i3')
        T.assert_almost_equal(fv, 0, 15, 'sla_flotin, v3')
        T.assert_equal(j, -1, 'sla_flotin, j3')
        i, fv, j = S.sla_flotin(s, i)
        T.assert_equal(i, 19, 'sla_flotin, i4')
        T.assert_almost_equal(fv, 1000, 15, 'sla_flotin, v4')
        T.assert_equal(j, 0, 'sla_flotin, j4')
        i, fv, j = S.sla_flotin(s, i)
        T.assert_equal(i, 22, 'sla_flotin, i5')
        T.assert_almost_equal(fv, -4, 15, 'sla_flotin, v5')
        T.assert_equal(j, -1, 'sla_flotin, j5')
        i, fv, j = S.sla_flotin(s, i)
        T.assert_equal(i, 28, 'sla_flotin, i6')
        T.assert_almost_equal(fv, 2000, 15, 'sla_flotin, v6')
        T.assert_equal(j, 0, 'sla_flotin, j6')
        i, fv, j = S.sla_flotin(s, i)
        T.assert_equal(i, 34, 'sla_flotin, i7')
        # this is different than in slalib_test.f since 'fv'
        # is output only and the value doesn't pass through
        T.assert_almost_equal(fv, 0.0, 15, 'sla_flotin, v7')
        T.assert_equal(j, 2, 'sla_flotin, j7')
        i = 1
        dv = 0
        i, dv, j = S.sla_dfltin(s, i)
        T.assert_equal(i, 10, 'sla_dfltin, i1')
        T.assert_almost_equal(dv, 12.345, 12, 'sla_dfltin, v1')
        T.assert_equal(j, 0, 'sla_dfltin, j1')
        i, dv, j = S.sla_dfltin(s, i)
        T.assert_equal(i, 12, 'sla_dfltin, i2')
        # this is different than in slalib_test.f since 'dv'
        # is output only and the value doesn't pass through
        T.assert_almost_equal(dv, 0.0, 15, 'sla_dfltin, v2')
        T.assert_equal(j, 1, 'sla_dfltin, j2')
        i, dv, j = S.sla_dfltin(s, i)
        T.assert_equal(i, 16, 'sla_dfltin, i3')
        T.assert_almost_equal(dv, 0, 15, 'sla_dfltin, v3')
        T.assert_equal(j, -1, 'sla_dfltin, j3')
        i, dv, j = S.sla_dfltin(s, i)
        T.assert_equal(i, 19, 'sla_dfltin, i4')
        T.assert_almost_equal(dv, 1000, 15, 'sla_dfltin, v4')
        T.assert_equal(j, 0, 'sla_dfltin, j4')
        i, dv, j = S.sla_dfltin(s, i)
        T.assert_equal(i, 22, 'sla_dfltin, i5')
        T.assert_almost_equal(dv, -4, 15, 'sla_dfltin, v5')
        T.assert_equal(j, -1, 'sla_dfltin, j5')
        i, dv, j = S.sla_dfltin(s, i)
        T.assert_equal(i, 28, 'sla_dfltin, i6')
        T.assert_almost_equal(dv, 2000, 15, 'sla_dfltin, v6')
        T.assert_equal(j, 0, 'sla_dfltin, j6')
        i, dv, j = S.sla_dfltin(s, i)
        T.assert_equal(i, 34, 'sla_dfltin, i7')
        # this is different than in slalib_test.f since 'dv'
        # is output only and the value doesn't pass through
        T.assert_almost_equal(dv, 0.0, 15, 'sla_dfltin, v7')
        T.assert_equal(j, 2, 'sla_dfltin, j7')

    def testgaleq(self):
        dr, dd = S.sla_galeq(5.67, -1.23)
        T.assert_almost_equal(dr, 0.04729270418071426, 12, 'sla_galeq, dr')
        T.assert_almost_equal(dd, -0.7834003666745548, 12, 'sla_galeq, dd')

    def testgalsup(self):
        dsl, dsb = S.sla_galsup(6.1, -1.4)
        T.assert_almost_equal(dsl, 4.567933268859171, 12, 'sla_galsup, dsl')
        T.assert_almost_equal(dsb, -0.01862369899731829, 12, 'sla_galsup, dsb')

    def testge50(self):
        dr, dd = S.sla_ge50(6.1, -1.55)
        T.assert_almost_equal(dr, 0.1966825219934508, 12, 'sla_ge50, dr')
        T.assert_almost_equal(dd, -0.4924752701678960, 12, 'sla_ge50, dd')

    def testgmst(self):
        T.assert_almost_equal(S.sla_gmst(43999.999), 3.9074971356487318,
                              9, 'sla_gmst')
        T.assert_almost_equal(S.sla_gmsta(43999, 0.999), 3.9074971356487318,
                              12, 'sla_gmsta')

    def testintin(self):
        s = '  -12345, , -0  2000  +     '
        i = 1
        n = 0
        i, n, j = S.sla_intin(s, i)
        T.assert_equal(i, 10, 'sla_intin, i1')
        T.assert_equal(n, -12345, 'sla_intin, v1')
        T.assert_equal(j, -1, 'sla_intin, j1')
        i, n, j = S.sla_intin(s, i)
        T.assert_equal(i, 12, 'sla_intin, i2')
        # this is different than in slalib_test.f since 'n'
        # is output only and the value doesn't pass through
        T.assert_equal(n, 0, 'sla_intin, v2')
        T.assert_equal(j, 1, 'sla_intin, j2')
        i, n, j = S.sla_intin(s, i)
        T.assert_equal(i, 17, 'sla_intin, i3')
        T.assert_equal(n, 0, 'sla_intin, v3')
        T.assert_equal(j, -1, 'sla_intin, j3')
        i, n, j = S.sla_intin(s, i)
        T.assert_equal(i, 23, 'sla_intin, i4')
        T.assert_equal(n, 2000, 'sla_intin, v4')
        T.assert_equal(j, 0, 'sla_intin, j4')
        i, n, j = S.sla_intin(s, i)
        T.assert_equal(i, 29, 'sla_intin, i5')
        # this is different than in slalib_test.f since 'n'
        # is output only and the value doesn't pass through
        T.assert_equal(n, 0, 'sla_intin, v5')
        T.assert_equal(j, 2, 'sla_intin, j5')

    def testkbj(self):
        k = safe_str('?')
        e = 1950
        k, j = S.sla_kbj(-1, e)
        T.assert_equal(k, safe_str(' '), 'sla_kbj, jb1')
        T.assert_equal(j, 1, 'sla_kbj, j1')
        k, j = S.sla_kbj(0, e)
        T.assert_equal(k, safe_str('B'), 'sla_kbj, jb2')
        T.assert_equal(j, 0, 'sla_kbj, j2')
        k, j = S.sla_kbj(1, e)
        T.assert_equal(k, safe_str('B'), 'sla_kbj, jb3')
        T.assert_equal(j, 0, 'sla_kbj, j3')
        k, j = S.sla_kbj(2, e)
        T.assert_equal(k, safe_str('J'), 'sla_kbj, jb4')
        T.assert_equal(j, 0, 'sla_kbj, j4')
        k, j = S.sla_kbj(3, e)
        T.assert_equal(k, safe_str(' '), 'sla_kbj, jb5')
        T.assert_equal(j, 1, 'sla_kbj, j5')
        e = 2000
        k, j = S.sla_kbj(0, e)
        T.assert_equal(k, safe_str('J'), 'sla_kbj, jb6')
        T.assert_equal(j, 0, 'sla_kbj, j6')
        k, j = S.sla_kbj(1, e)
        T.assert_equal(k, safe_str('B'), 'sla_kbj, jb7')
        T.assert_equal(j, 0, 'sla_kbj, j7')
        k, j = S.sla_kbj(2, e)
        T.assert_equal(k, safe_str('J'), 'sla_kbj, jb8')
        T.assert_equal(j, 0, 'sla_kbj, j8')

    def testmap(self):
        ra, da = S.sla_map(6.123, -0.999, 1.23e-5, -0.987e-5,
                           0.123, 32.1, 1999, 43210.9)
        T.assert_almost_equal(ra, 6.117130429775647, 12, 'sla_map, ra')
        T.assert_almost_equal(da, -1.000880769038632, 12, 'sla_map, da')
        amprms = S.sla_mappa(2020, 45012.3)
        T.assert_almost_equal(amprms[0], -37.884188911704310, 11, 'sla_mappa, amprms(1)')
        T.assert_almost_equal(amprms[1], -0.7888341859486424, 7, 'sla_mappa, amprms(2)')
        T.assert_almost_equal(amprms[2], 0.5405321789059870, 7, 'sla_mappa, amprms(3)')
        T.assert_almost_equal(amprms[3], 0.2340784267119091, 7, 'sla_mappa, amprms(4)')
        T.assert_almost_equal(amprms[4], -0.8067807553217332071, 7, 'sla_mappa, amprms(5)')
        T.assert_almost_equal(amprms[5], 0.5420884771236513880, 7, 'sla_mappa, amprms(6)')
        T.assert_almost_equal(amprms[6], 0.2350423277034460899, 7, 'sla_mappa, amprms(7)')
        T.assert_almost_equal(amprms[7], 1.999729469227807e-8, 12, 'sla_mappa, amprms(8)')
        T.assert_almost_equal(amprms[8], -6.035531043691568494e-5, 12, 'sla_mappa, amprms(9)')
        T.assert_almost_equal(amprms[9], -7.381891582591552377e-5, 11, 'sla_mappa, amprms(10)')
        T.assert_almost_equal(amprms[10], -3.200897749853207412e-5, 11, 'sla_mappa, amprms(11)')
        T.assert_almost_equal(amprms[11], 0.9999999949417148, 11, 'sla_mappa, amprms(12)')
        T.assert_almost_equal(amprms[12], 0.9999566751478850, 11, 'sla_mappa, amprms(13)')
        T.assert_almost_equal(amprms[13], -8.537361890149777e-3, 11, 'sla_mappa, amprms(14)')
        T.assert_almost_equal(amprms[14], -3.709619811228171e-3, 11, 'sla_mappa, amprms(15)')
        T.assert_almost_equal(amprms[15], 8.537308717676752e-3, 11, 'sla_mappa, amprms(16)')
        T.assert_almost_equal(amprms[16], 0.9999635560607690, 11, 'sla_mappa, amprms(17)')
        T.assert_almost_equal(amprms[17], -3.016886324169151e-5, 11, 'sla_mappa, amprms(18)')
        T.assert_almost_equal(amprms[18], 3.709742180572510e-3, 11, 'sla_mappa, amprms(19)')
        T.assert_almost_equal(amprms[19], -1.502613373498668e-6, 11, 'sla_mappa, amprms(20)')
        T.assert_almost_equal(amprms[20], 0.9999931188816729, 11, 'sla_mappa, amprms(21)')
        ra, da = S.sla_mapqk(1.234, -0.987, -1.2e-5, -0.99, 0.75, -23.4, amprms)
        T.assert_almost_equal(ra, 1.223337584930993, 11, 'sla_mapqk, ra')
        T.assert_almost_equal(da, 0.5558838650379129, 11, 'sla_mapqk, da')
        ra, da = S.sla_mapqkz(6.012, 1.234, amprms)
        T.assert_almost_equal(ra, 6.006091119756597, 11, 'sla_mapqkz, ra')
        T.assert_almost_equal(da, 1.23045846622498, 11, 'sla_mapqkz, da')

    def testmoon(self):
        pv = S.sla_moon(1999, 365, 0.9)
        T.assert_almost_equal(pv[0], -2.155729505970773e-3, 6, 'sla_moon, (1)')
        T.assert_almost_equal(pv[1], -1.538107758633427e-3, 6, 'sla_moon, (2)')
        T.assert_almost_equal(pv[2], -4.003940552689305e-4, 6, 'sla_moon, (3)')
        T.assert_almost_equal(pv[3],  3.629209419071314e-9, 12, 'sla_moon, (4)')
        T.assert_almost_equal(pv[4], -4.989667166259157e-9, 12, 'sla_moon, (5)')
        T.assert_almost_equal(pv[5], -2.160752457288307e-9, 12, 'sla_moon, (6)')

    def testnut(self):
        rmatn = S.sla_nut(46012.34)
        ans = N.asarray([[9.999999969492166e-1, 7.166577986249302e-5, 3.107382973077677e-5],
                         [-7.166503970900504e-5, 9.999999971483732e-1, -2.381965032461830e-5],
                         [-3.107553669598237e-5, 2.381742334472628e-5, 9.999999992335206818e-1]])
        T.assert_array_almost_equal(rmatn, ans, 12, 'sla_nut, rmatn')
        dpsi, deps, eps0 = S.sla_nutc(50123.4)
        T.assert_almost_equal(dpsi, 3.523550954747999709e-5, 17, 'sla_nutc, dpsi')
        T.assert_almost_equal(deps, -4.143371566683342e-5, 17, 'sla_nutc, deps')
        T.assert_almost_equal(eps0, 0.4091014592901651, 12, 'sla_nutc, eps0')
        dpsi, deps, eps0 = S.sla_nutc80(50123.4)
        T.assert_almost_equal(dpsi, 3.537714281665945321e-5, 17, 'sla_nutc80, dpsi')
        T.assert_almost_equal(deps, -4.140590085987148317e-5, 17, 'sla_nutc80, deps')
        T.assert_almost_equal(eps0, 0.4091016349007751, 12, 'sla_nutc80, eps0')

    def testobs(self):
        n = 0
        c = safe_str('MMT')
        c, name, w, p, h = S.sla_obs(n, c)
        T.assert_equal(c.strip(), safe_str('MMT'), 'sla_obs, 1/c')
        T.assert_equal(name.strip(), safe_str('MMT 6.5m, Mt Hopkins'), 'sla_obs, 1/name')
        T.assert_almost_equal(w, 1.935300584055477, 8, 'sla_obs, 1/w')
        T.assert_almost_equal(p, 0.5530735081550342238, 10, 'sla_obs, 1/p')
        T.assert_almost_equal(h, 2608, 10, 'sla_obs, 1/h')
        n = 61
        c = 20*' '
        c, name, w, p, h = S.sla_obs(n, c)
        T.assert_equal(c.strip(), safe_str('KECK1'), 'sla_obs, 2/c')
        T.assert_equal(name.strip(), safe_str('Keck 10m Telescope #1'), 'sla_obs, 2/name')
        T.assert_almost_equal(w, 2.713545757918895, 8, 'sla_obs, 2/w')
        T.assert_almost_equal(p, 0.3460280563536619, 8, 'sla_obs, 2/p')
        T.assert_almost_equal(h, 4160, 10, 'sla_obs, 2/h')
        n = 83
        c = 20*' '
        c, name, w, p, h = S.sla_obs(n, c)
        T.assert_equal(c.strip(), safe_str('MAGELLAN2'), 'sla_obs, 3/c')
        T.assert_equal(name.strip(), safe_str('Magellan 2, 6.5m, Las Campanas'), 'sla_obs, 3/name')
        T.assert_almost_equal(w, 1.233819305534497, 8, 'sla_obs, 3/w')
        T.assert_almost_equal(p, -0.506389344359954, 8, 'sla_obs, 3/p')
        T.assert_almost_equal(h, 2408, 10, 'sla_obs, 3/h')
        n = 84
        c = 20*' '
        c, name, w, p, h = S.sla_obs(n, c)
        T.assert_equal(name.strip(), safe_str('?'), 'sla_obs, 4/name')

    def testpa(self):
        T.assert_almost_equal(S.sla_pa(-1.567, 1.5123, 0.987),
                              -1.486288540423851, 12, 'sla_pa')
        T.assert_almost_equal(S.sla_pa(0, 0.789, 0.789),
                              0, 0, 'sla_pa, zenith')

    def testpcd(self):
        disco = 178.585
        x = 0.0123
        y = -0.00987
        x, y = S.sla_pcd(disco, x, y)
        T.assert_almost_equal(x, 0.01284630845735895, 14, 'sla_pcd, x')
        T.assert_almost_equal(y, -0.01030837922553926, 14, 'sla_pcd, y')
        x, y = S.sla_unpcd(disco, x, y)
        T.assert_almost_equal(x, 0.0123, 14, 'sla_unpcd, x')
        T.assert_almost_equal(y, -0.00987, 14, 'sla_unpcd, y')

    def testpda2h(self):
        h1, j1, h2, j2 = S.sla_pda2h(-0.51, -1.31, 3.1)
        T.assert_almost_equal(h1, -0.1161784556585304927, 14, 'sla_pda2h, h1')
        T.assert_equal(j1, 0, 'sla_pda2h, j1')
        T.assert_almost_equal(h2, -2.984787179226459, 13, 'sla_pda2h, h2')
        T.assert_equal(j2, 0, 'sla_pda2h, j2')

    def testpdq2h(self):
        h1, j1, h2, j2 = S.sla_pdq2h(0.9, 0.2, 0.1)
        T.assert_almost_equal(h1, 0.1042809894435257, 14, 'sla_pdq2h, h1')
        T.assert_equal(j1, 0, 'sla_pdq2h, j1')
        T.assert_almost_equal(h2, 2.997450098818439, 13, 'sla_pdq2h, h2')
        T.assert_equal(j2, 0, 'sla_pdq2h, j2')

    def testpercom(self):
        inlist = N.zeros(3, N.int32)
        for i in range(11):
            inlist, j = S.sla_combn(5, inlist)
            #print inlist, j
        T.assert_equal(j, 1, 'sla_combn, j')
        T.assert_equal(inlist[0], 1, 'sla_combn, list(1)')
        T.assert_equal(inlist[1], 2, 'sla_combn, list(2)')
        T.assert_equal(inlist[2], 3, 'sla_combn, list(3)')
        istate = N.zeros(4, N.int32)
        iorder = N.zeros(4, N.int32)
        istate[0] = -1
        for i in range(25):
            istate, iorder, j = S.sla_permut(istate)
            #print istate, iorder, j
        T.assert_equal(j, 1, 'sla_permut, j')
        T.assert_equal(iorder[0], 4, 'sla_permut, iorder(1)')
        T.assert_equal(iorder[1], 3, 'sla_permut, iorder(2)')
        T.assert_equal(iorder[2], 2, 'sla_permut, iorder(3)')
        T.assert_equal(iorder[3], 1, 'sla_permut, iorder(4)')

    def testplanet(self):
        u, j = S.sla_el2ue(50000, 1, 49000, 0.1, 2, 0.2,
                           3, 0.05, 3, 0.003312)
        ans1 = N.asarray([1.000878908362435284, -0.3336263027874777288,
                          50000, 2.840425801310305210, 0.1264380368035014224,
                          -0.2287711835229143197, -0.01301062595106185195,
                          0.5657102158104651697, 0.2189745287281794885,
                          2.852427310959998500, -0.01552349065435120900, 50000, 0])
        T.assert_array_almost_equal(u, ans1, 12, 'sla_el2ue, u')
        T.assert_equal(j, 0, 'sla_el2ue, j')
        epoch, orbinc, anode, perih, aorq, e, aorl, j = \
               S.sla_pertel(2, 43000, 43200, 43000, 0.2, 3, 4, 5, 0.02, 6)
        T.assert_almost_equal(epoch, 43200, 10, 'sla_pertel, epoch')
        T.assert_almost_equal(orbinc, 0.1995661466545422381, 7, 'sla_pertel, orbinc')
        T.assert_almost_equal(anode, 2.998052737821591215, 7, 'sla_pertel, anode')
        T.assert_almost_equal(perih, 4.009516448441143636, 6, 'sla_pertel, perih')
        T.assert_almost_equal(aorq, 5.014216294790922323, 7, 'sla_pertel, aorq')
        T.assert_almost_equal(e, 0.02281386258309823607, 7, 'sla_pertel, e')
        T.assert_almost_equal(aorl, 0.01735248648779583748, 6, 'sla_pertel, aorl')
        T.assert_equal(j, 0, 'sla_pertel, j')
        u, j = S.sla_pertue(50100, u)
        ans2 = N.asarray([1.000000000000000, -0.3329769417028020949, 50100,
                          2.638884303608524597, 1.070994304747824305,
                          0.1544112080167568589, -0.2188240619161439344,
                          0.5207557453451906385, 0.2217782439275216936,
                          2.852118859689216658, 0.01452010174371893229, 50100, 0])
        T.assert_array_almost_equal(u, ans2, 12, 'sla_pertue, u')
        T.assert_equal(j, 0, 'sla_pertue, j')
        pv, j = S.sla_planel(50600, 2, 50500, 0.1, 3, 5, 2, 0.3, 4, 0)
        T.assert_almost_equal(pv[0], 1.947628959288897677, 12, 'sla_planel, pv(1)')
        T.assert_almost_equal(pv[1], -1.013736058752235271, 12, 'sla_planel, pv(2)')
        T.assert_almost_equal(pv[2], -0.3536409947732733647, 12, 'sla_planel, pv(3)')
        T.assert_almost_equal(pv[3], 2.742247411571786194e-8, 19, 'sla_planel, pv(4)')
        T.assert_almost_equal(pv[4], 1.170467244079075911e-7, 19, 'sla_planel, pv(5)')
        T.assert_almost_equal(pv[5], 3.709878268217564005e-8, 19, 'sla_planel, pv(6)')
        T.assert_equal(j, 0, 'sla_planel, j')
        pv, j = S.sla_planet(1e6, 0)
        T.assert_array_almost_equal(pv, N.zeros(6.0), 15, 'sla_planet, pv 1')
        T.assert_equal(j, -1, 'sla_planet, j 1')
        pv, j = S.sla_planet(1e6, 10)
        T.assert_equal(j, -1, 'sla_planet, j 2')
        pv, j = S.sla_planet(-320000, 3)
        T.assert_almost_equal(pv[0], 0.9308038666827242603, 11, 'sla_planet, pv(1) 3')
        T.assert_almost_equal(pv[1], 0.3258319040252137618, 11, 'sla_planet, pv(2) 3')
        T.assert_almost_equal(pv[2], 0.1422794544477122021, 11, 'sla_planet, pv(3) 3')
        T.assert_almost_equal(pv[3], -7.441503423889371696e-8, 17, 'sla_planet, pv(4) 3')
        T.assert_almost_equal(pv[4], 1.699734557528650689e-7, 17, 'sla_planet, pv(5) 3')
        T.assert_almost_equal(pv[5], 7.415505123001430864e-8, 17, 'sla_planet, pv(6) 3')
        T.assert_equal(j, 1, 'sla_planet, j 3')
        pv, j = S.sla_planet(43999.9, 1)
        T.assert_almost_equal(pv[0], 0.2945293959257422246, 11, 'sla_planet, pv(1) 4')
        T.assert_almost_equal(pv[1], -0.2452204176601052181, 11, 'sla_planet, pv(2) 4')
        T.assert_almost_equal(pv[2], -0.1615427700571978643, 11, 'sla_planet, pv(3) 4')
        T.assert_almost_equal(pv[3], 1.636421147459047057e-7, 18, 'sla_planet, pv(4) 4')
        T.assert_almost_equal(pv[4], 2.252949422574889753e-7, 18, 'sla_planet, pv(5) 4')
        T.assert_almost_equal(pv[5], 1.033542799062371839e-7, 18, 'sla_planet, pv(6) 4')
        T.assert_equal(j, 0, 'sla_planet, j 4')
        ra, dec, r, j = S.sla_plante(50600, -1.23, 0.456, 2, 50500,
                                     0.1, 3, 5, 2, 0.3, 4, 0)
        T.assert_almost_equal(ra, 6.222958101333794007, 10, 'sla_plante, ra')
        T.assert_almost_equal(dec, 0.01142220305739771601, 10, 'sla_plante, dec')
        T.assert_almost_equal(r, 2.288902494080167624, 8, 'sla_plante, r')
        T.assert_equal(j, 0, 'sla_plante, j')
        u = N.asarray([1.0005, -0.3, 55000, 2.8, 0.1, -0.2, -0.01, 0.5,
                       0.22, 2.8, -0.015, 55001, 0])
        ra, dec, r, j = S.sla_plantu(55001, -1.23, 0.456, u)
        T.assert_almost_equal(ra, 0.3531814831241686647, 9, 'sla_plantu, ra')
        T.assert_almost_equal(dec, 0.06940344580567131328, 9, 'sla_plantu, dec')
        T.assert_almost_equal(r, 3.031687170873274464, 8, 'sla_plantu, r')
        T.assert_equal(j, 0, 'sla_plantu, j')
        pv = N.asarray([0.3, -0.2, 0.1, -0.9e-7, 0.8e-7, -0.7e-7])
        jform, epoch, orbinc, anode, perih, aorq, e, aorl, dm, j = \
               S.sla_pv2el(pv, 50000, 0.00006, 1)
        T.assert_equal(jform, 1, 'sla_pv2el, jform')
        T.assert_almost_equal(epoch, 50000, 10, 'sla_pv2el, epoch')
        T.assert_almost_equal(orbinc, 1.52099895268912, 12, 'sla_pv2el, orbinc')
        T.assert_almost_equal(anode, 2.720503180538650, 12, 'sla_pv2el, anode')
        T.assert_almost_equal(perih, 2.194081512031836, 12, 'sla_pv2el, perih')
        T.assert_almost_equal(aorq, 0.2059371035373771, 12, 'sla_pv2el, aorq')
        T.assert_almost_equal(e, 0.9866822985810528, 12, 'sla_pv2el, e')
        T.assert_almost_equal(aorl, 0.2012758344836794, 12, 'sla_pv2el, aorl')
        T.assert_almost_equal(dm, 0.1840740507951820, 12, 'sla_pv2el, dm')
        T.assert_equal(j, 0, 'sla_pv2el, j')
        u, j = S.sla_pv2ue(pv, 50000, 0.00006)
        T.assert_almost_equal(u[0], 1.00006, 12, 'sla_pv2ue, u(1)')
        T.assert_almost_equal(u[1], -4.856142884511782, 12, 'sla_pv2ue, u(2)')
        T.assert_almost_equal(u[2], 50000, 12, 'sla_pv2ue, u(3)')
        T.assert_almost_equal(u[3], 0.3, 12, 'sla_pv2ue, u(4)')
        T.assert_almost_equal(u[4], -0.2, 12, 'sla_pv2ue, u(5)')
        T.assert_almost_equal(u[5], 0.1, 12, 'sla_pv2ue, u(6)')
        T.assert_almost_equal(u[6], -0.4520378601821727, 12, 'sla_pv2ue, u(7)')
        T.assert_almost_equal(u[7], 0.4018114312730424, 12, 'sla_pv2ue, u(8)')
        T.assert_almost_equal(u[8], -.3515850023639121, 12, 'sla_pv2ue, u(9)')
        T.assert_almost_equal(u[9], 0.3741657386773941, 12, 'sla_pv2ue, u(10)')
        T.assert_almost_equal(u[10], -0.2511321445456515, 12, 'sla_pv2ue, u(11)')
        T.assert_almost_equal(u[11], 50000, 12, 'sla_pv2ue, u(12)')
        T.assert_almost_equal(u[12], 0, 12, 'sla_pv2ue, u(13)')
        T.assert_equal(j, 0, 'sla_pv2ue, j')
        ra, dec, diam = S.sla_rdplan(40999.9, 0, 0.1, -0.9)
        T.assert_almost_equal(ra, 5.772270359389275837, 7, 'sla_rdplan, ra 0')
        T.assert_almost_equal(dec, -0.2089207338795416192, 7, 'sla_rdplan, dec 0')
        T.assert_almost_equal(diam, 9.415338935229717875e-3, 14, 'sla_rdplan, diam 0')
        ra, dec, diam = S.sla_rdplan(41999.9, 1, 1.1, -0.9)
        T.assert_almost_equal(ra, 3.866363420052936653, 7, 'sla_rdplan, ra 1')
        T.assert_almost_equal(dec, -0.2594430577550113130, 7, 'sla_rdplan, dec 1')
        T.assert_almost_equal(diam, 4.638468996795023071e-5, 14, 'sla_rdplan, diam 1')
        ra, dec, diam = S.sla_rdplan(42999.9, 2, 2.1, 0.9)
        T.assert_almost_equal(ra, 2.695383203184077378, 7, 'sla_rdplan, ra 2')
        T.assert_almost_equal(dec, 0.2124044506294805126, 7, 'sla_rdplan, dec 2')
        T.assert_almost_equal(diam, 4.892222838681000389e-5, 14, 'sla_rdplan, diam 2')
        ra, dec, diam = S.sla_rdplan(43999.9, 3, 3.1, 0.9)
        T.assert_almost_equal(ra, 2.908326678461540165, 7, 'sla_rdplan, ra 3')
        T.assert_almost_equal(dec, 0.08729783126905579385, 7, 'sla_rdplan, dec 3')
        T.assert_almost_equal(diam, 8.581305866034962476e-3, 14, 'sla_rdplan, diam 3')
        ra, dec, diam = S.sla_rdplan(44999.9, 4, -0.1, 1.1)
        T.assert_almost_equal(ra, 3.429840787472851721, 7, 'sla_rdplan, ra 4')
        T.assert_almost_equal(dec, -0.06979851055261161013, 7, 'sla_rdplan, dec 4')
        T.assert_almost_equal(diam, 4.540536678439300199e-5, 14, 'sla_rdplan, diam 4')
        ra, dec, diam = S.sla_rdplan(45999.9, 5, -1.1, 0.1)
        T.assert_almost_equal(ra, 4.864669466449422548, 7, 'sla_rdplan, ra 5')
        T.assert_almost_equal(dec, -0.4077714497908953354, 7, 'sla_rdplan, dec 5')
        T.assert_almost_equal(diam, 1.727945579027815576e-4, 14, 'sla_rdplan, diam 5')
        ra, dec, diam = S.sla_rdplan(46999.9, 6, -2.1, -0.1)
        T.assert_almost_equal(ra, 4.432929829176388766, 7, 'sla_rdplan, ra 6')
        T.assert_almost_equal(dec, -0.3682820877854730530, 7, 'sla_rdplan, dec 6')
        T.assert_almost_equal(diam, 8.670829016099083311e-5, 14, 'sla_rdplan, diam 6')
        ra, dec, diam = S.sla_rdplan(47999.9, 7, -3.1, -1.1)
        T.assert_almost_equal(ra, 4.894972492286818487, 7, 'sla_rdplan, ra 7')
        T.assert_almost_equal(dec, -0.4084068901053653125, 7, 'sla_rdplan, dec 7')
        T.assert_almost_equal(diam, 1.793916783975974163e-5, 14, 'sla_rdplan, diam 7')
        ra, dec, diam = S.sla_rdplan(48999.9, 8, 0, 0)
        T.assert_almost_equal(ra, 5.066050284760144000, 7, 'sla_rdplan, ra 8')
        T.assert_almost_equal(dec, -0.3744690779683850609, 7, 'sla_rdplan, dec 8')
        T.assert_almost_equal(diam, 1.062210086082700563e-5, 14, 'sla_rdplan, diam 8')
        ra, dec, diam = S.sla_rdplan(49999.9, 9, 0, 0)
        T.assert_almost_equal(ra, 4.179543143097200945, 7, 'sla_rdplan, ra 9')
        T.assert_almost_equal(dec, -0.1258021632894033300, 7, 'sla_rdplan, dec 9')
        T.assert_almost_equal(diam, 5.034057475664904352e-7, 14, 'sla_rdplan, diam 9')
        jform, epoch, orbinc, anode, perih, aorq, e, aorl, dm, j = S.sla_ue2el(u, 1)
        T.assert_equal(jform, 1, 'sla_ue2el, jform')
        T.assert_almost_equal(epoch, 50000.00000000000, 10, 'sla_pv2el, epoch')
        T.assert_almost_equal(orbinc, 1.520998952689120, 12, 'sla_ue2el, orbinc')
        T.assert_almost_equal(anode, 2.720503180538650, 12, 'sla_ue2el, anode')
        T.assert_almost_equal(perih, 2.194081512031836, 12, 'sla_ue2el, perih')
        T.assert_almost_equal(aorq, 0.2059371035373771, 12, 'sla_ue2el, aorq')
        T.assert_almost_equal(e, 0.9866822985810528, 12, 'sla_ue2el, e')
        T.assert_almost_equal(aorl, 0.2012758344836794, 12, 'sla_ue2el, aorl')
        T.assert_equal(j, 0, 'sla_ue2el, j')
        u, pv, j = S.sla_ue2pv(50010, u)
        T.assert_almost_equal(u[0], 1.00006, 12, 'sla_ue2pv, u(1)')
        T.assert_almost_equal(u[1], -4.856142884511782111, 12, 'sla_ue2pv, u(2)')
        T.assert_almost_equal(u[2], 50000, 12, 'sla_ue2pv, u(3)')
        T.assert_almost_equal(u[3], 0.3, 12, 'sla_ue2pv, u(4)')
        T.assert_almost_equal(u[4], -0.2, 12, 'sla_ue2pv, u(5)')
        T.assert_almost_equal(u[5], 0.1, 12, 'sla_ue2pv, u(6)')
        T.assert_almost_equal(u[6], -0.4520378601821727110, 12, 'sla_ue2pv, u(7)')
        T.assert_almost_equal(u[7], 0.4018114312730424097, 12, 'sla_ue2pv, u(8)')
        T.assert_almost_equal(u[8], -0.3515850023639121085, 12, 'sla_ue2pv, u(9)')
        T.assert_almost_equal(u[9], 0.3741657386773941386, 12, 'sla_ue2pv, u(10)')
        T.assert_almost_equal(u[10], -0.2511321445456515061, 12, 'sla_ue2pv, u(11)')
        T.assert_almost_equal(u[11], 50010.00000000000, 12, 'sla_ue2pv, u(12)')
        T.assert_almost_equal(u[12], 0.7194308220038886856, 12, 'sla_ue2pv, u(13)')
        T.assert_almost_equal(pv[0], 0.07944764084631667011, 12, 'sla_ue2pv, pv(1)')
        T.assert_almost_equal(pv[1], -0.04118141077419014775, 12, 'sla_ue2pv, pv(2)')
        T.assert_almost_equal(pv[2], 0.002915180702063625400, 12, 'sla_ue2pv, pv(3)')
        T.assert_almost_equal(pv[3], -0.6890132370721108608e-6, 18,'sla_ue2pv, pv(4)')
        T.assert_almost_equal(pv[4], 0.4326690733487621457e-6, 18, 'sla_ue2pv, pv(5)')
        T.assert_almost_equal(pv[5], -0.1763249096254134306e-6, 18, 'sla_ue2pv, pv(6)')
        T.assert_equal(j, 0, 'sla_ue2pv, j')

    def testpm(self):
        r1, d1 = S.sla_pm(5.43, -0.87, -0.33e-5, 0.77e-5, 0.7,
                          50.3*365.2422/365.25, 1899, 1943)
        T.assert_almost_equal(r1, 5.429855087793875, 12, 'sla_pm, r')
        T.assert_almost_equal(d1, -0.8696617307805072, 12, 'sla_pm, d')

    def testpolmo(self):
        elong, phi, daz = S.sla_polmo(0.7, -0.5, 1e-6, -2e-6)
        T.assert_almost_equal(elong,  0.7000004837322044, 12, 'sla_polmo, elong')
        T.assert_almost_equal(phi, -0.4999979467222241, 12, 'sla_polmo, phi')
        T.assert_almost_equal(daz,  1.008982781275728e-6, 12, 'sla_polmo, daz')

    def testprebn(self):
        rmatp = S.sla_prebn(1925, 1975)
        ans = N.asarray([[9.999257613786738e-1, -1.117444640880939e-2, -4.858341150654265e-3],
                         [1.117444639746558e-2,  9.999375635561940e-1, -2.714797892626396e-5],
                         [4.858341176745641e-3, -2.714330927085065e-5,  9.999881978224798e-1]])
        T.assert_array_almost_equal(rmatp, ans, 12, 'sla_prebn, (1,1)')

    def testprec(self):
        rmatp = S.sla_prec(1925, 1975)
        ans = N.asarray([[9.999257249850045e-1, -1.117719859160180e-2, -4.859500474027002e-3],
                         [1.117719858025860e-2,  9.999375327960091e-1, -2.716114374174549e-5],
                         [4.859500500117173e-3, -2.715647545167383e-5,  9.999881921889954e-1]])
        T.assert_array_almost_equal(rmatp, ans, 12, 'sla_prec, (1,1)')
        rmatp = S.sla_precl(1925, 1975)
        ans = N.asarray([[9.999257331781050e-1, -1.117658038434041e-2, -4.859236477249598e-3],
                         [1.117658037299592e-2,  9.999375397061558e-1, -2.715816653174189e-5],
                         [4.859236503342703e-3, -2.715349745834860e-5,  9.999881934719490e-1]])
        T.assert_array_almost_equal(rmatp, ans, 12, 'sla_precl, (1,1)')

    def testpreces(self):
        ra = 6.28
        dc = -1.123
        ra, dc = S.sla_preces('fk4', 1925, 1950, ra, dc)
        T.assert_almost_equal(ra, 0.002403604864728447, 12, 'sla_preces, r')
        T.assert_almost_equal(dc, -1.120570643322045, 12, 'sla_preces, d')
        ra = 0.0123
        dc = 1.0987
        ra, dc = S.sla_preces('fk5', 2050, 1990, ra, dc)
        T.assert_almost_equal(ra, 6.282003602708382, 12, 'sla_preces, r')
        T.assert_almost_equal(dc, 1.092870326188383, 12, 'sla_preces, d')

    def testprenut(self):
        rmatpn = S.sla_prenut(1985, 50123.4567)
        ans = N.asarray([[9.999962358680738e-1, -2.516417057665452e-3, -1.093569785342370e-3],
                         [2.516462370370876e-3,  9.999968329010883e-1,  4.006159587358310e-5],
                         [1.093465510215479e-3, -4.281337229063151e-5,  9.999994012499173e-1]])
        T.assert_array_almost_equal(rmatpn, ans, 12, 'sla_prenut, (3,3)')

    def testpvobs(self):
        pv = S.sla_pvobs(0.5123, 3001, -0.567)
        T.assert_almost_equal(pv[0], 0.3138647803054939e-4, 16, 'sla_pvobs, (1)')
        T.assert_almost_equal(pv[1],-0.1998515596527082e-4, 16, 'sla_pvobs, (2)')
        T.assert_almost_equal(pv[2], 0.2078572043443275e-4, 16, 'sla_pvobs, (3)')
        T.assert_almost_equal(pv[3], 0.1457340726851264e-8, 20, 'sla_pvobs, (4)')
        T.assert_almost_equal(pv[4], 0.2288738340888011e-8, 20, 'sla_pvobs, (5)')
        T.assert_almost_equal(pv[5], 0, 0, 'sla_pvobs, (6)')

    def testrange(self):
        T.assert_almost_equal(S.sla_range(-4.0), 2.283185307179586, 6, 'sla_range')
        T.assert_almost_equal(S.sla_drange(-4.0), 2.283185307179586, 12, 'sla_drange')

    def testranorm(self):
        T.assert_almost_equal(S.sla_ranorm(-0.1), 6.183185307179587, 5, 'sla_ranorm, 1')
        T.assert_almost_equal(S.sla_dranrm(-0.1), 6.183185307179587, 12, 'sla_dranrm, 2')

    def testrcc(self):
        T.assert_almost_equal(S.sla_rcc(48939.123, 0.76543, 5.0123, 5525.242, 3190),
                              -1.280131613589158e-3, 15, 'sla_rcc')

    def testref(self):
        ref = S.sla_refro(1.4, 3456.7, 280, 678.9, 0.9, 0.55, -0.3, 0.006, 1e-9)
        T.assert_almost_equal(ref, 0.00106715763018568, 12, 'sla_refro, o')
        ref = S.sla_refro(1.4, 3456.7, 280, 678.9, 0.9, 1000, -0.3, 0.006, 1e-9)
        T.assert_almost_equal(ref, 0.001296416185295403, 12, 'sla_refro, r')
        refa, refb = S.sla_refcoq(275.9, 709.3, 0.9, 101)
        T.assert_almost_equal(refa, 2.324736903790639e-4, 12, 'sla_refcoq, a/r')
        T.assert_almost_equal(refb, -2.442884551059e-7, 15, 'sla_refcoq, b/r')
        refa, refb = S.sla_refco(2111.1, 275.9, 709.3, 0.9, 101, -1.03, 0.0067, 1e-12)
        T.assert_almost_equal(refa, 2.324673985217244e-4, 12, 'sla_refco, a/r')
        T.assert_almost_equal(refb, -2.265040682496e-7, 15, 'sla_refco, b/r')
        refa, refb = S.sla_refcoq(275.9, 709.3, 0.9, 0.77)
        T.assert_almost_equal(refa, 2.007406521596588e-4, 12, 'sla_refcoq, a')
        T.assert_almost_equal(refb, -2.264210092590e-7, 15, 'sla_refcoq, b')
        refa, refb = S.sla_refco(2111.1, 275.9, 709.3, 0.9, 0.77, -1.03, 0.0067, 1e-12)
        T.assert_almost_equal(refa, 2.007202720084551e-4, 12, 'sla_refco, a')
        T.assert_almost_equal(refb, -2.223037748876e-7, 15, 'sla_refco, b')
        refa2, refb2 = S.sla_atmdsp(275.9, 709.3, 0.9, 0.77, refa, refb, 0.5)
        T.assert_almost_equal(refa2, 2.034523658888048e-4, 12, 'sla_atmdsp, a')
        T.assert_almost_equal(refb2, -2.250855362179e-7, 15, 'sla_atmdsp, b')
        vu = S.sla_dcs2c(0.345, 0.456)
        vr = S.sla_refv(vu, refa, refb)
        T.assert_almost_equal(vr[0], 0.8447487047790478, 12, 'sla_refv, x1')
        T.assert_almost_equal(vr[1], 0.3035794890562339, 12, 'sla_refv, y1')
        T.assert_almost_equal(vr[2], 0.4407256738589851, 12, 'sla_refv, z1')
        vu = S.sla_dcs2c(3.7, 0.03)
        vr = S.sla_refv(vu, refa, refb)
        T.assert_almost_equal(vr[0], -0.8476187691681673, 12, 'sla_refv, x2')
        T.assert_almost_equal(vr[1], -0.5295354802804889, 12, 'sla_refv, y2')
        T.assert_almost_equal(vr[2],  0.0322914582168426, 12, 'sla_refv, z2')
        zr = S.sla_refz(0.567, refa, refb)
        T.assert_almost_equal(zr, 0.566872285910534, 12, 'sla_refz, hi el')
        zr = S.sla_refz(1.55, refa, refb)
        T.assert_almost_equal(zr, 1.545697350690958, 12, 'sla_refz, lo el')

    def testrv(self):
        T.assert_almost_equal(S.sla_rverot(-0.777, 5.67, -0.3, 3.19),
                              -0.1948098355075913, 6, 'sla_rverot')
        T.assert_almost_equal(S.sla_rvgalc(1.11, -0.99),
                              158.9630759840254, 3, 'sla_rvgalc')
        T.assert_almost_equal(S.sla_rvlg(3.97, 1.09),
                              -197.818762175363, 3, 'sla_rvlg')
        T.assert_almost_equal(S.sla_rvlsrd(6.01, 0.1),
                              -4.082811335150567, 4, 'sla_rvlsrd')
        T.assert_almost_equal(S.sla_rvlsrk(6.01, 0.1),
                              -5.925180579830265, 4, 'sla_rvlsrk')

    def testsep(self):
        d1 = r1 = N.asarray([1.0, 0.1, 0.2])
        d2 = r2 = N.asarray([-3.0, 1e-3, 0.2])
        ad1, bd1 = S.sla_dcc2s(d1)
        ad2, bd2 = S.sla_dcc2s(d2)
        T.assert_almost_equal(S.sla_dsep(ad1, bd1, ad2, bd2),
                              2.8603919190246608, 7, 'sla_dsep')
        T.assert_almost_equal((S.sla_sep(ad1, bd1, ad2, bd2)),
                              2.8603919190246608, 4, 'sla_sep')
        T.assert_almost_equal(S.sla_dsepv(d1, d2),
                              2.8603919190246608, 7, 'sla_dsepv')
        T.assert_almost_equal((S.sla_sepv(r1, r2)),
                              2.8603919190246608, 4, 'sla_sepv')

    def testsmat(self):
        a = N.asarray([[2.22,     1.6578,     1.380522],
                       [1.6578,   1.380522,   1.22548578],
                       [1.380522, 1.22548578, 1.1356276122]],
                      order='Fortran')
        v = N.asarray([2.28625, 1.7128825, 1.429432225])
        a, v, d, j, iw = S.sla_smat(a, v, N.empty(3.0, dtype=N.float32))
        ans = N.asarray([[18.02550629769198, -52.16386644917280607, 34.37875949717850495],
                         [-52.16386644917280607, 168.1778099099805627, -118.0722869694232670],
                         [34.37875949717850495, -118.0722869694232670, 86.50307003740151262]],
                        order='Fortran')
        T.assert_array_almost_equal(a, ans, 2, 'sla_smat, a(3,3)')
        ans = N.asarray([1.002346480763383, 0.03285594016974583489, 0.004760688414885247309])
        T.assert_array_almost_equal(v, ans, 4, 'sla_smat, v(3)')
        T.assert_almost_equal(d, 0.003658344147359863, 4, 'sla_smat, d')
        T.assert_equal(j, 0, 'sla_smat, j')

    def testsupgal(self):
        dl, db = S.sla_supgal(6.1, -1.4)
        T.assert_almost_equal(dl, 3.798775860769474, 12, 'sla_supgal, dl')
        T.assert_almost_equal(db, -0.1397070490669407, 12, 'sla_supgal, db')

    def testsvd(self):
        mp = 10
        np = 6
        nc = 7
        m = 5
        n = 4
        a = N.empty((m, n), order='Fortran')
        b = N.empty(m)
        for ii in range(m):
            val = 0.5 * (ii + 1.0)
            b[ii] = 23 - 3.0 * val - 11.0 * math.sin(val) + 13.0 * math.cos(val)
            a[ii,0] = 1.0
            a[ii,1] = val
            a[ii,2] = math.sin(val)
            a[ii,3] = math.cos(val)
        a, w, v, work, j = S.sla_svd(m, n, a)
        if a[0,0] > 0.0:
            a = -a
            v = -v
        ans = N.asarray([[-0.21532492989299, 0.67675050651267,-0.37267876361644, 0.58330405917160],
                         [-0.33693420368121, 0.48011695963936, 0.62656568539705,-0.17479918328198],
                         [-0.44396825906047, 0.18255923809825, 0.02228154115994,-0.51743308030238],
                         [-0.53172583816951,-0.16537863535943,-0.61134201569990,-0.28871221824912],
                         [-0.60022523682867,-0.50081781972404, 0.30706750690326, 0.52736124480318]])
        T.assert_array_almost_equal(a, ans, 12, 'sla_svd, a')
        ans = N.asarray([4.57362714220621, 1.64056393111226, 0.03999179717447, 0.37267332634218])
        T.assert_array_almost_equal(w, ans, 12, 'sla_svd, w')
        ans = N.asarray([[-0.46531525230679, 0.41036514115630,-0.70279526907678, 0.34808185338758],
                         [-0.80342444002914,-0.29896472833787, 0.46592932810178, 0.21917828721921],
                         [-0.36564497020801, 0.28066812941896,-0.03324480702665,-0.88680546891402],
                         [0.06553350971918 , 0.81452191085452, 0.53654771808636, 0.21065602782287]])
        T.assert_array_almost_equal(v, ans, 12, 'sla_svd, v')
        work, x = S.sla_svdsol(b, a, w, v)
        ans = N.asarray([23.0, -3.0, -11.0, 13.0])
        T.assert_array_almost_equal(x, ans, 12, 'sla_svdsol, x')
        work, c = S.sla_svdcov(w, v)
        ans = N.asarray([[ 309.77269378273270,-204.22043941662150,  12.43704316907477,-235.12299986206710],
                         [-204.22043941662150, 136.14695961108110, -11.10167446246327, 156.54937371198730],
                         [  12.43704316907477, -11.10167446246327,   6.38909830090602, -12.41424302586736],
                         [-235.12299986206710, 156.54937371198730, -12.41424302586736, 180.56719842359560]])
        T.assert_array_almost_equal(c, ans, 10, 'sla_svdcov, c')

    def testtp(self):
        r0 = 3.1
        d0 = -0.9
        r1 = r0 + 0.2
        d1 = d0 - 0.1
        x, y, j = S.sla_s2tp(r1, d1, r0, d0)
        T.assert_almost_equal(x, 0.1086112301590404, 6, 'sla_s2tp, x')
        T.assert_almost_equal(y, -0.1095506200711452, 6, 'sla_s2tp, y')
        T.assert_equal(j, 0, 'sla_s2tp, j')
        r2, d2 = S.sla_tp2s(x, y, r0, d0)
        T.assert_almost_equal(((r2 - r1)), 0, 6, 'sla_tp2s, r')
        T.assert_almost_equal(((d2 - d1)), 0, 6, 'sla_tp2s, d')
        r01, d01, r02, d02, j = S.sla_tps2c(x, y, r2, d2)
        T.assert_almost_equal(r01,  3.1, 6, 'sla_tps2c, r1')
        T.assert_almost_equal(d01, -0.9, 6, 'sla_tps2c, d1')
        T.assert_almost_equal(r02, 0.3584073464102072, 6, 'sla_tps2c, r2')
        T.assert_almost_equal(d02, -2.023361658234722, 6, 'sla_tps2c, d2')
        T.assert_equal(j, 1, 'sla_tps2c, n')
        dr0 = 3.1
        dd0 = -0.9
        dr1 = dr0 + 0.2
        dd1 = dd0 - 0.1
        dx, dy, j = S.sla_ds2tp(dr1, dd1, dr0, dd0)
        T.assert_almost_equal(dx, 0.1086112301590404, 12, 'sla_ds2tp, x')
        T.assert_almost_equal(dy, -0.1095506200711452, 12, 'sla_ds2tp, y')
        T.assert_equal(j, 0, 'sla_ds2tp, j')
        dr2, dd2 = S.sla_dtp2s(dx, dy, dr0, dd0)
        T.assert_almost_equal(dr2 - dr1, 0, 12, 'sla_dtp2s, r')
        T.assert_almost_equal(dd2 - dd1, 0, 12, 'sla_dtp2s, d')
        dr01, dd01, dr02, dd02, j = S.sla_dtps2c(dx, dy, dr2, dd2)
        T.assert_almost_equal(dr01,  3.1, 12, 'sla_dtps2c, r1')
        T.assert_almost_equal(dd01, -0.9, 12, 'sla_dtps2c, d1')
        T.assert_almost_equal(dr02, 0.3584073464102072, 12, 'sla_dtps2c, r2')
        T.assert_almost_equal(dd02, -2.023361658234722, 12, 'sla_dtps2c, d2')
        T.assert_equal(j, 1, 'sla_dtps2c, n')

    def testtpv(self):
        xi = -0.1
        eta = 0.055
        rxi = xi
        reta = eta
        x = -0.7
        y = -0.13
        z = math.sqrt(1.0 - x * x - y * y)
        rv = N.asarray([x, y, z])
        v = N.asarray([x, y, z])
        x = -0.72
        y = -0.16
        z = math.sqrt(1.0 - x * x - y * y)
        rv0 = N.asarray([x, y, z])
        v0 = N.asarray([x, y, z])
        rtv = S.sla_tp2v(rxi, reta, rv0)
        T.assert_almost_equal(rtv[0], -0.700887428128, 6, 'sla_tp2v, v(1)')
        T.assert_almost_equal(rtv[1], -0.05397407,     6, 'sla_tp2v, v(2)')
        T.assert_almost_equal(rtv[2],  0.711226836562, 6, 'sla_tp2v, v(3)')
        tv = S.sla_dtp2v(xi, eta, v0)
        T.assert_almost_equal(tv[0], -0.7008874281280771,  13, 'sla_dtp2v, v(1)')
        T.assert_almost_equal(tv[1], -0.05397406827952735, 13, 'sla_dtp2v, v(2)')
        T.assert_almost_equal(tv[2],  0.7112268365615617,  13, 'sla_dtp2v, v(3)')
        rtxi, rteta, j = S.sla_v2tp(rv, rv0)
        T.assert_almost_equal(rtxi, -0.02497229197, 6, 'sla_v2tp, xi')
        T.assert_almost_equal(rteta, 0.03748140764, 6, 'sla_v2tp, eta')
        T.assert_equal(j, 0, 'sla_v2tp, j')
        txi, teta, j = S.sla_dv2tp(v, v0)
        T.assert_almost_equal(txi, -0.02497229197023852, 13, 'sla_dv2tp, xi')
        T.assert_almost_equal(teta, 0.03748140764224765, 13, 'sla_dv2tp, eta')
        T.assert_equal(j, 0, 'sla_dv2tp, j')
        rtv01, rtv02, j = S.sla_tpv2c(rxi, reta, rv)
        T.assert_almost_equal(rtv01[0], -0.7074573732537283,  6, 'sla_tpv2c, v01(1)')
        T.assert_almost_equal(rtv01[1], -0.2372965765309941,  6, 'sla_tpv2c, v01(2)')
        T.assert_almost_equal(rtv01[2],  0.6657284730245545,  6, 'sla_tpv2c, v01(3)')
        T.assert_almost_equal(rtv02[0], -0.6680480104758149,  6, 'sla_tpv2c, v02(1)')
        T.assert_almost_equal(rtv02[1], -0.02915588494045333, 6, 'sla_tpv2c, v02(2)')
        T.assert_almost_equal(rtv02[2],  0.7435467638774610,  6, 'sla_tpv2c, v02(3)')
        T.assert_equal(j, 1, 'sla_tpv2c, n')
        tv01, tv02, j = S.sla_dtpv2c(xi, eta, v)
        T.assert_almost_equal(tv01[0], -0.7074573732537283,  13, 'sla_dtpv2c, v01(1)')
        T.assert_almost_equal(tv01[1], -0.2372965765309941,  13, 'sla_dtpv2c, v01(2)')
        T.assert_almost_equal(tv01[2], 0.6657284730245545,   13, 'sla_dtpv2c, v01(3)')
        T.assert_almost_equal(tv02[0], -0.6680480104758149,  13, 'sla_dtpv2c, v02(1)')
        T.assert_almost_equal(tv02[1], -0.02915588494045333, 13, 'sla_dtpv2c, v02(2)')
        T.assert_almost_equal(tv02[2], 0.7435467638774610,   13, 'sla_dtpv2c, v02(3)')
        T.assert_equal(j, 1, 'sla_dtpv2c, n')

    def testvecmat(self):
        # Single precision
        av = N.asarray([-0.123, 0.0987, 0.0654])
        rm1 = S.sla_av2m(av)
        ans = N.asarray([[0.9930075842721269,  0.05902743090199868, -0.1022335560329612], 
                         [-0.07113807138648245, 0.9903204657727545, -0.1191836812279541], 
                         [0.09420887631983825,  0.1256229973879967,  0.9875948309655174]])
        T.assert_array_almost_equal(rm1, ans, 6, 'sla_av2m')
        rm2 = S.sla_euler('yzy', 2.345, -0.333, 2.222)
        ans = N.asarray([[-0.1681574770810878, 0.1981362273264315, 0.9656423242187410], 
                         [-0.2285369373983370, 0.9450659587140423,-0.2337117924378156],
                         [-0.9589024617479674,-0.2599853247796050,-0.1136384607117296]])
        T.assert_array_almost_equal(rm2, ans, 6, 'sla_euler')
        rm = S.sla_mxm(rm2, rm1)
        ans = N.asarray([[-0.09010460088585805, 0.3075993402463796, 0.9472400998581048],
                         [-0.3161868071070688,  0.8930686362478707,-0.3200848543149236],
                         [-0.9444083141897035, -0.3283459407855694,0.01678926022795169]])
        T.assert_array_almost_equal(rm, ans, 6, 'sla_mxm')
        v1 = S.sla_cs2c(3.0123, -0.999)
        ans = N.asarray([-0.5366267667260525, 0.06977111097651444, -0.8409302618566215])
        T.assert_array_almost_equal(v1, ans, 6, 'sla_cs2c')
        v2 = S.sla_mxv(rm1, v1)
        v3 = S.sla_mxv(rm2, v2)
        ans = N.asarray([-0.7267487768696160, 0.5011537352639822, 0.4697671220397141])
        T.assert_array_almost_equal(v3, ans, 6, 'sla_mxv')
        v4 = S.sla_imxv(rm, v3)
        ans = N.asarray([-0.5366267667260526, 0.06977111097651445, -0.8409302618566215])
        T.assert_array_almost_equal(v4, ans, 6, 'sla_imxv')
        v5 = S.sla_m2av(rm)
        ans = N.asarray([0.006889040510209034, -1.577473205461961, 0.5201843672856759])
        T.assert_array_almost_equal(v5, ans, 6, 'sla_m2av')
        v5 *= 1000.0
        v6, vm = S.sla_vn(v5)
        ans = N.asarray([0.004147420704640065, -0.9496888606842218, 0.3131674740355448])
        T.assert_array_almost_equal(v6, ans, 6, 'sla_vn, v')
        T.assert_almost_equal(vm, 1661.042127339937, 3, 'sla_vn, m')
        T.assert_almost_equal(S.sla_vdv(v6, v1), -0.3318384698006295, 6, 'sla_vdv')
        v7 = S.sla_vxv(v6, v1)
        ans = N.asarray([0.7767720597123304, -0.1645663574562769, -0.5093390925544726])
        T.assert_array_almost_equal(v7, ans, 6, 'sla_vxv')
        # Double precision
        av = N.asarray([-0.123, 0.0987, 0.0654])
        rm1 = S.sla_dav2m(av)
        ans = N.asarray([[0.9930075842721269,  0.05902743090199868, -0.1022335560329612], 
                         [-0.07113807138648245, 0.9903204657727545, -0.1191836812279541], 
                         [0.09420887631983825,  0.1256229973879967,  0.9875948309655174]])
        T.assert_array_almost_equal(rm1, ans, 12, 'sla_dav2m')
        rm2 = S.sla_deuler('yzy', 2.345, -0.333, 2.222)
        ans = N.asarray([[-0.1681574770810878, 0.1981362273264315, 0.9656423242187410], 
                         [-0.2285369373983370, 0.9450659587140423,-0.2337117924378156],
                         [-0.9589024617479674,-0.2599853247796050,-0.1136384607117296]])
        T.assert_array_almost_equal(rm2, ans, 12, 'sla_deuler')
        rm = S.sla_dmxm(rm2, rm1)
        ans = N.asarray([[-0.09010460088585805, 0.3075993402463796, 0.9472400998581048],
                         [-0.3161868071070688,  0.8930686362478707,-0.3200848543149236],
                         [-0.9444083141897035, -0.3283459407855694,0.01678926022795169]])
        T.assert_array_almost_equal(rm, ans, 12, 'sla_dmxm')
        v1 = S.sla_dcs2c(3.0123, -0.999)
        ans = N.asarray([-0.5366267667260525, 0.06977111097651444, -0.8409302618566215])
        T.assert_array_almost_equal(v1, ans, 12, 'sla_dcs2c')
        v2 = S.sla_dmxv(rm1, v1)
        v3 = S.sla_dmxv(rm2, v2)
        ans = N.asarray([-0.7267487768696160, 0.5011537352639822, 0.4697671220397141])
        T.assert_array_almost_equal(v3, ans, 12, 'sla_dmxv')
        v4 = S.sla_dimxv(rm, v3)
        ans = N.asarray([-0.5366267667260526, 0.06977111097651445, -0.8409302618566215])
        T.assert_array_almost_equal(v4, ans, 12, 'sla_dimxv')
        v5 = S.sla_dm2av(rm)
        ans = N.asarray([0.006889040510209034, -1.577473205461961, 0.5201843672856759])
        T.assert_array_almost_equal(v5, ans, 12, 'sla_dm2av')
        v5 *= 1000.0
        v6, vm = S.sla_dvn(v5)
        ans = N.asarray([0.004147420704640065, -0.9496888606842218, 0.3131674740355448])
        T.assert_array_almost_equal(v6, ans, 12, 'sla_dvn, v')
        T.assert_almost_equal(vm, 1661.042127339937, 3, 'sla_dvn, m')
        T.assert_almost_equal(S.sla_dvdv(v6, v1), -0.3318384698006295, 12, 'sla_dvdv')
        v7 = S.sla_dvxv(v6, v1)
        ans = N.asarray([0.7767720597123304, -0.1645663574562769, -0.5093390925544726])
        T.assert_array_almost_equal(v7, ans, 12, 'sla_dvxv')

    def testzd(self):
        T.assert_almost_equal(S.sla_zd(-1.023, -0.876, -0.432),
                              0.8963914139430839, 12, 'sla_zd')

if __name__ == '__main__':
    unittest.main()
