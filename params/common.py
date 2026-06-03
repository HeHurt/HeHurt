from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pybamm
from scipy.interpolate import interp1d


PARAMS_DIR = Path(__file__).resolve().parent
REFERENCE_TEMPERATURE = 298.15
FARADAY_CONSTANT = 96485.33212
SOC_GRID = np.linspace(0, 1, 500)
BASE_CRACKING_RATE_AI2020 = 2.1939307272313407e-21


@lru_cache(maxsize=None)
def _load_profile(file_name):
    data = pd.read_csv(PARAMS_DIR / file_name, header=None)
    interpolator = interp1d(data[0], data[1], fill_value="extrapolate")
    return SOC_GRID, np.asarray(interpolator(SOC_GRID), dtype=float)


def build_ocp_function(file_name, *, name, offset=0.0):
    def ocp(sto):
        soc, values = _load_profile(file_name)
        return pybamm.Interpolant(soc, values + offset, sto, name=name, interpolator="cubic")

    return ocp


def arrhenius_factor(activation_energy, temperature):
    return pybamm.exp(
        activation_energy / pybamm.constants.R
        * (1 / REFERENCE_TEMPERATURE - 1 / temperature)
    )


def build_diffusivity(d_ref, activation_energy, *, multiplier=1.0):
    def diffusivity(sto, temperature):
        energy = activation_energy(temperature) if callable(activation_energy) else activation_energy
        return multiplier * d_ref * arrhenius_factor(energy, temperature)

    return diffusivity


def build_exchange_current_density(m_ref, activation_energy, *, c_l_ref=1e3, multiplier=1.0):
    def exchange_current_density(c_e, c_s_surf, c_s_max, temperature):
        energy = activation_energy(temperature) if callable(activation_energy) else activation_energy
        return (
            multiplier
            * m_ref
            * arrhenius_factor(energy, temperature)
            * (c_e / c_l_ref) ** 0.5
            * c_s_surf ** 0.5
            * (c_s_max - c_s_surf) ** 0.5
            * FARADAY_CONSTANT
        )

    return exchange_current_density


def build_cracking_rate(t_factor=1, *, base_rate=BASE_CRACKING_RATE_AI2020, activation_energy=10000):
    def cracking_rate_ai2020(temperature):
        return base_rate * t_factor * arrhenius_factor(activation_energy, temperature)

    return cracking_rate_ai2020


def plating_exchange_current_density_okane2020(c_e, c_li, temperature):
    k_plating = pybamm.Parameter("Lithium plating kinetic rate constant [m.s-1]")
    return k_plating * arrhenius_factor(11178, temperature)


def electrolyte_diffusivity_nyman2008_arrhenius(c_e, temperature):
    p = [5.55347004e-20, -2.75740663e-16, 2.48896764e-13, 3.50298875e-10]
    diffusivity = p[0] * 1000**3 + p[1] * 1000**2 + p[2] * 1000 + p[3]
    return diffusivity * arrhenius_factor(0, temperature)


def electrolyte_conductivity(c_e, temperature):
    sigma_e = 0.1297 * (c_e / 1000) ** 3 - 2.51 * (c_e / 1000) ** 1.5 + 3.329 * (c_e / 1000)
    return sigma_e * arrhenius_factor(0, temperature)


def select_by_requested_temperature(temperature, low_value, high_value, *, threshold=298.0):
    return low_value if temperature < threshold else high_value


def lfp_entropic(sto):
    return (
        -1.39262467e-01 * (sto**8)
        + 6.02393209e-01 * (sto**7)
        - 1.07457345e00 * (sto**6)
        + 1.02239130e00 * (sto**5)
        - 5.59871056e-01 * (sto**4)
        + 1.76951351e-01 * (sto**3)
        - 3.02491476e-02 * (sto**2)
        + 2.11209531e-03 * sto
        + 8.62182125e-06
    )


def graphite_entropic(sto):
    return (
        2.29827815e01 * (sto**9)
        - 9.60265948e01 * (sto**8)
        + 1.66281204e02 * (sto**7)
        - 1.54174573e02 * (sto**6)
        + 8.24040908e01 * (sto**5)
        - 2.53676448e01 * (sto**4)
        + 4.20323260e00 * (sto**3)
        - 3.03662776e-01 * (sto**2)
        + 4.46024654e-04 * sto
        + 6.00000000e-04
    )