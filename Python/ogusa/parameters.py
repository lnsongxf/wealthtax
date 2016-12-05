'''
------------------------------------------------------------------------
Last updated 8/1/2017

This file sets parameters for the model run.

This py-file calls the following other file(s):
            income.py
            demographics.py
------------------------------------------------------------------------
'''

'''
------------------------------------------------------------------------
Import Packages
------------------------------------------------------------------------
'''
import os
import json
import numpy as np
import scipy.interpolate as si
import scipy.ndimage.filters as filter
import demographics as dem
import income as inc
import pickle
import txfunc
import elliptical_u_est as ellip
import matplotlib.pyplot as plt

'''
------------------------------------------------------------------------
Parameters
------------------------------------------------------------------------
Model Parameters:
------------------------------------------------------------------------
S            = integer, number of economically active periods an individual lives
J            = integer, number of different ability groups
T            = integer, number of time periods until steady state is reached
BW           = integer, number of time periods in the budget window
lambdas      = [J,] vector, percentiles for ability groups
imm_rates    = [J,T+S] array, immigration rates by age and year
starting_age = integer, age agents enter population
ending age   = integer, maximum age agents can live until
E            = integer, age agents become economically active
beta_annual  = scalar, discount factor as an annual rate
beta         = scalar, discount factor for model period
sigma        = scalar, coefficient of relative risk aversion
alpha        = scalar, capital share of income
Z            = scalar, total factor productivity parameter in firms' production
               function
delta_annual = scalar, depreciation rate as an annual rate
delta        = scalar, depreciation rate for model period
ltilde       = scalar, measure of time each individual is endowed with each
               period
g_y_annual   = scalar, annual growth rate of technology
g_y          = scalar, growth rate of technology for a model period
frisch       = scalar, Frisch elasticity that is used to fit ellipitcal utility
               to constant Frisch elasticity function
b_ellipse    = scalar, value of b for elliptical fit of utility function
k_ellipse    = scalar, value of k for elliptical fit of utility function
upsilon      = scalar, value of omega for elliptical fit of utility function
------------------------------------------------------------------------
Tax Parameters:
------------------------------------------------------------------------
mean_income_data = scalar, mean income from IRS data file used to calibrate income tax
etr_params       = [S,BW,#tax params] array, parameters for effective tax rate function
mtrx_params      = [S,BW,#tax params] array, parameters for marginal tax rate on
                    labor income function
mtry_params      = [S,BW,#tax params] array, parameters for marginal tax rate on
                    capital income function
h_wealth         = scalar, wealth tax parameter h (scalar)
m_wealth         = scalar, wealth tax parameter m (scalar)
p_wealth         = scalar, wealth tax parameter p (scalar)
tau_bq           = [J,] vector, bequest tax
tau_payroll      = scalar, payroll tax rate
retire           = integer, age at which individuals eligible for retirement benefits
------------------------------------------------------------------------
Simulation Parameters:
------------------------------------------------------------------------
MINIMIZER_TOL = scalar, tolerance level for the minimizer in the calibration of chi parameters
MINIMIZER_OPTIONS = dictionary, dictionary for options to put into the minimizer, usually
                    to set a max iteration
PLOT_TPI     = boolean, =Ture if plot the path of K as TPI iterates (for debugging purposes)
maxiter      = integer, maximum number of iterations that SS and TPI solution methods will undergo
mindist_SS   = scalar, tolerance for SS solution
mindist_TPI  = scalar, tolerance for TPI solution
nu           = scalar, contraction parameter in SS and TPI iteration process
               representing the weight on the new distribution
flag_graphs  = boolean, =True if produce graphs in demographic, income,
               wealth, and labor files (True=graph)
chi_b_guess  = [J,] vector, initial guess of \chi^{b}_{j} parameters
               (if no calibration occurs, these are the values that will be used for \chi^{b}_{j})
chi_n_guess  = [S,] vector, initial guess of \chi^{n}_{s} parameters
               (if no calibration occurs, these are the values that will be used for \chi^{n}_{s})
------------------------------------------------------------------------
Demographics and Ability variables:
------------------------------------------------------------------------
omega        = [T+S,S] array, time path of stationary distribution of economically active population by age
g_n_ss       = scalar, steady state population growth rate
omega_SS     = [S,] vector, stationary steady state population distribution
surv_rate    = [S,] vector, survival rates by age
rho          = [S,] vector, mortality rates by age
g_n_vector   = [T+S,] vector, growth rate in economically active pop for each period in transition path
e            = [S,J] array, normalized effective labor units by age and ability type
------------------------------------------------------------------------
'''
def get_parameters(baseline, reform, guid, user_modifiable):
    '''
    --------------------------------------------------------------------
    This function sets the parameters for the full model.
    --------------------------------------------------------------------

    INPUTS:
    baseline        = boolean, =True if baseline tax policy, =False if reform
    guid            = string, id for reform run
    user_modifiable = boolean, =True if allow user modifiable parameters
    metadata        = boolean, =True if use metadata file for parameter
                       values (rather than what is entered in parameters below)

    OTHER FUNCTIONS AND FILES CALLED BY THIS FUNCTION:
    read_tax_func_estimate()
    elliptical_u_est.estimation()
    read_parameter_metadata()

    OBJECTS CREATED WITHIN FUNCTION:
    See parameters defined above
    allvars = dictionary, dictionary with all parameters defined in this function

    RETURNS: allvars

    OUTPUT: None
    --------------------------------------------------------------------
    '''
    # Model Parameters
    S = int(80) #S<30 won't meet necessary tolerances
    J = int(7)
    T = int(3 * S)
    BW = int(10)
    lambdas = np.array([.25, .25, .2, .1, .1, .09, .01])
    #lambdas = np.array([0.5, 0.5])
    #lambdas = np.array([1.,])
    start_year = 2016
    starting_age = 20
    ending_age = 100
    E = int(starting_age * (S / float(ending_age - starting_age)))
    beta_annual = .96 # Carroll (JME, 2009)
    beta = beta_annual ** (float(ending_age - starting_age) / S)
    sigma = 3.0
    alpha = .35 # many use 0.33, but many find that capitals share is
                # increasing (e.g. Elsby, Hobijn, and Sahin (BPEA, 2013))
    Z = 1.0
    delta_annual = .05 # approximately the value from Kehoe calibration
                       # exercise: http://www.econ.umn.edu/~tkehoe/classes/calibration-04.pdf
    delta = 1 - ((1 - delta_annual) ** (float(ending_age - starting_age) / S))
    ltilde = 1.0
    g_y_annual = 0.03
    g_y = (1 + g_y_annual)**(float(ending_age - starting_age) / S) - 1
    #   Ellipse parameters
    frisch = 1.5 # Frisch elasticity consistent with Peterman (Econ Inquiry, 2016)
    b_ellipse, upsilon = ellip.estimation(frisch,ltilde)
    k_ellipse = 0 # this parameter is just a level shifter in utlitiy - irrelevant for analysis


    # Tax parameters:
    mean_income_data = 84377.0

    etr_params = np.zeros((S,BW,10))
    mtrx_params = np.zeros((S,BW,10))
    mtry_params = np.zeros((S,BW,10))

    #baseline values - reform values determined in execute.py
    a_tax_income = 3.03452713268985e-06
    b_tax_income = .222
    c_tax_income = 133261.0
    d_tax_income = 0.219

    etr_params[:,:,0] = a_tax_income
    etr_params[:,:,1] = b_tax_income
    etr_params[:,:,2] = c_tax_income
    etr_params[:,:,3] = d_tax_income

    mtrx_params = etr_params
    mtry_params = etr_params


    #   Wealth tax params
    #       These are non-calibrated values, h and m just need
    #       need to be nonzero to avoid errors. When p_wealth
    #       is zero, there is no wealth tax.
    if reform == 2:
        # wealth tax reform values
        p_wealth = 0.025 #0.0095091#0.025
        h_wealth = 0.305509008443123
        m_wealth = 2.16050687852062

    else:
        #baseline values
        h_wealth = 0.1
        m_wealth = 1.0
        p_wealth = 0.0



    #   Bequest and Payroll Taxes
    tau_bq = np.zeros(J)
    tau_payroll = 0.15
    retire = np.round(9.0 * S / 16.0) - 1

    # Simulation Parameters
    MINIMIZER_TOL = 1e-14
    MINIMIZER_OPTIONS = None
    PLOT_TPI = False
    maxiter = 250
    mindist_SS = 1e-9
    mindist_TPI = 1e-9 #2e-5
    nu = .4
    flag_graphs = False
    #   Calibration parameters
    # These guesses are close to the calibrated values - with sigma = 3, frisch = 1/1.5
    # chi_b_guess = np.array([0.04003265, 0.11, 0.2, 0.95,
    #    90., 750., 11700.])
    # chi_b_guess =np.array([1.0, 1.0])*80
    chi_b_guess =np.array([1.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0, 4780.])
    # chi_b_guess =np.array([0.3, 0.3, 2., 14.,
    #         12.5, 98., 2150.])*13.0 # this hits about 6% interest and very close on wealth moments for
    #                                 # Frisch 1.5 and sigma 2.0 ** but with old demographics file!!!

    # chi_b_guess =np.array([0.001, 0.007, 0.3, 4.,
    #     3.5, 125., 5550.])*180.0 # this hits about 6% interest and very close on wealth moments for
    #                             # Frisch 1.5 and sigma 3.0 ** but with old demographics file!!!

    # chi_n_guess_80=([38.35115078, 33.47310428, 25.63926049, 26.90508485, 24.63035262,
    #              23.35906224, 22.65935099, 22.03392052, 21.62478355, 22.13535233,
    #              21.69560359, 21.64146739, 21.39697892, 21.19206356, 20.94355578,
    #              20.64768419, 20.53979306, 20.36804443, 19.10932758, 18.98558476,
    #              20.60688512, 20.50078038, 20.2256643, 19.95992287, 19.6673207,
    #              19.6776809, 19.6120645, 19.60992325, 19.56024565, 19.54786468,
    #              19.54453725, 19.55393179, 19.5669215, 19.56866264, 21.63426928,
    #              21.66758321, 21.82479238, 21.94810588, 21.95270906, 22.24409932,
    #              22.43579108, 23.22300316, 24.19041652, 24.98193805, 26.37655839,
    #              29.64082279, 30.46066408, 31.50891934, 33.12827027, 32.89220568,
    #              38.06447857, 39.29539292, 40.07733956, 35.20596752, 35.98608886,
    #              37.06253229, 37.43632457, 37.92002918, 38.63115739, 39.4902618,
    #              37.11109829, 40.04153446, 40.86680947, 41.73712424, 42.62100261,
    #              43.37768981, 45.38048878, 46.22250725, 50.21146199, 51.04962263,
    #              53.86561018, 53.8970376, 61.83187581, 64.87158401, 66.90804378,
    #              68.07048742, 71.2752016, 73.56799731, 74.94650456, 76.6191262])
    chi_n_guess_80=([40.35115078, 35.47310428, 27.63926049, 26.90508485, 24.63035262,
                 21.35906224, 20.65935099, 19.03392052, 19.62478355, 19.13535233,
                 17.69560359, 16.64146739, 16.64146739, 16.64146739, 16.64146739,
                 16.64146739, 15.64146739, 14.64146739, 14.64146739, 14.98558476,
                 14.60688512, 14.50078038, 14.2256643, 14.95992287, 14.6673207,
                 13.6776809, 13.6120645, 13.60992325, 13.56024565, 13.54786468,
                 13.54453725, 13.55393179, 13.5669215, 13.56866264, 14.63426928,
                 15.66758321, 15.82479238, 15.94810588, 16.95270906, 18.24409932,
                 19.43579108, 19.22300316, 19.19041652, 20.98193805, 20.98193805,
                 20.98193805, 21.98193805, 22.0, 22.0, 22.0,
                 21.0, 21.0, 21.0, 21.0, 21.0,
                 21.0, 21.0, 20.0, 20.0, 19.0,
                 19.0, 19.0, 18.0, 18.0, 18.0,
                 18.0, 18.0, 18.0, 18.0, 17.0,
                 17.0, 17.0, 17.0, 17.0, 17.0,
                 17.0, 16.0, 16.0, 16.0, 16.0])



#     chi_n_guess_80=([40.4,
# 37.9,
# 34.5,
# 30,
# 26.4,
# 24.3,
# 22.2,
# 20.4,
# 19.8,
# 19.3,
# 18.8,
# 17.8,
# 17,
# 16.6,
# 16.6,
# 16.6,
# 16.3,
# 15.6,
# 15,
# 14.8,
# 14.7,
# 14.7,
# 14.4,
# 14.6,
# 14.6,
# 14.4,
# 14,
# 13.6,
# 13.6,
# 13.6,
# 13.6,
# 13.5,
# 13.6,
# 13.6,
# 13.9,
# 14.6,
# 15.4,
# 15.8,
# 16.2,
# 17,
# 18.2,
# 19,
# 19.3,
# 19.8,
# 20.4,
# 21,
# 21.3,
# 21.7,
# 22,
# 22,
# 21.7,
# 21.3,
# 21,
# 21,
# 21,
# 21,
# 21,
# 20.7,
# 20.3,
# 19.7,
# 19.3,
# 19,
# 18.7,
# 18.3,
# 18,
# 18,
# 18,
# 18,
# 18,
# 17.7,
# 17.3,
# 17,
# 17,
# 17,
# 17,
# 17,
# 16.7,
# 16.3,
# 16,
# 16])

   # # Generate Income and Demographic parameters
   #  omega, g_n_ss, omega_SS, surv_rate, rho, g_n_vector, imm_rates, omega_S_preTP = get_pop_objs(
   #      E, S, T, 1, 100, 2016, flag_graphs)

    # Generate Income and Demographic parameters
    (omega, g_n_ss, omega_SS, surv_rate, rho, g_n_vector, imm_rates,
        omega_S_preTP) = dem.get_pop_objs(E, S, T, 1, 100, start_year,
        flag_graphs)

    # Interpolate chi_n_guesses and create omega_SS_80 if necessary
    if S == 80:
        chi_n_guess = chi_n_guess_80
        omega_SS_80 = omega_SS
    elif S < 80:
        age_midp_80 = np.linspace(20.5, 99.5, 80)
        chi_n_interp = si.interp1d(age_midp_80, chi_n_guess_80,
                       kind='cubic')
        newstep = 80.0 / S
        age_midp_S = np.linspace(20 + 0.5 * newstep,
                     100 - 0.5 * newstep, S)
        chi_n_guess = chi_n_interp(age_midp_S)
        (_, _, omega_SS_80, _, _, _, _,_) = dem.get_pop_objs(20, 80,
            320, 1, 100, start_year, False)

    # make pop constant
    # omega = np.tile(omega_SS.reshape(1,S),(T+S,1))
    # g_n_vector[:] = g_n_ss
    # imm_rates = np.tile(imm_rates[-1,:].reshape(1,S),(T+S,1))
    # omega_S_preTP = omega_SS


    # e = get_e(80, 7, 20, 100, np.array([.25, .25, .2, .1, .1, .09, .01]), flag_graphs)
    # e = e[:,:2]
    # # # need to turn 80x7 array into SxJ array
    # e /= (e * omega_SS.reshape(S, 1)
    #             * lambdas.reshape(1, J)).sum()

    e = inc.get_e_interp(S, omega_SS, omega_SS_80, lambdas, plot=False)

    # e_test = np.tile(np.reshape(e[:,3],(S,1)),(1,J))
    # e = e_test

    allvars = dict(locals())

    return allvars
