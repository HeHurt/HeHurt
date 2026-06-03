"""PyBaMM 生命周期 EIS 工作流。"""

import numpy as np
import pandas as pd
import pybamm

from .experiment_utils import build_power_step
from .simulation_common import _make_parameter_values
from .simulation_rpt import integrate_step_capacity_ah, snapshot_degradation_variables, step_mean_current


DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS = {
    "surface form": "differential",
    "SEI": "solvent-diffusion limited",
    "lithium plating": "partially reversible",
    "SEI on cracks": "true",
}


def _build_parameter_values(get_hithium_params, t_factor, temperature_k, double_layer_capacity):
    params = _make_parameter_values(
        get_hithium_params,
        t_factor,
        temperature_k,
        check_already_exists=False,
    )
    params["Negative electrode double-layer capacity [F.m-2]"] = double_layer_capacity
    params["Positive electrode double-layer capacity [F.m-2]"] = double_layer_capacity
    return params


def build_lifecycle_power_experiment(
    cycles,
    power_w,
    nominal_capacity_ah,
    temperature_k,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.5,
    rest_minutes=30,
    period_minutes=10,
    reference_voltage_v=3.2,
):
    """Build the strict constant-power lifecycle experiment used before EIS checkpoints."""
    cycle_steps = (
        build_power_step(
            direction="Charge",
            power_w=power_w,
            cutoff_voltage_v=charge_cutoff_v,
            nominal_capacity_ah=nominal_capacity_ah,
            period_minutes=period_minutes,
            reference_voltage_v=reference_voltage_v,
        ),
        f"Hold at {charge_cutoff_v:.2f} V until C/20 ({period_minutes:g} minute period)",
        f"Rest for {rest_minutes:g} minutes ({period_minutes:g} minute period)",
        build_power_step(
            direction="Discharge",
            power_w=power_w,
            cutoff_voltage_v=discharge_cutoff_v,
            nominal_capacity_ah=nominal_capacity_ah,
            period_minutes=period_minutes,
            reference_voltage_v=reference_voltage_v,
        ),
        f"Rest for {rest_minutes:g} minutes ({period_minutes:g} minute period)",
    )
    return pybamm.Experiment([cycle_steps] * cycles, temperature=temperature_k)


def _get_cycle_discharge_capacity_ah(cycle_solution, current_threshold=0.05):
    discharge_steps = [step for step in cycle_solution.steps if step_mean_current(step) > current_threshold]
    return sum(integrate_step_capacity_ah(step) for step in discharge_steps)


def _get_cycle_charge_current_a(cycle_solution, current_threshold=0.05):
    for step in cycle_solution.steps:
        mean_current = step_mean_current(step)
        if mean_current < -current_threshold:
            return abs(float(mean_current))
    raise ValueError("No charge step found in cycle_solution; cannot prepare a fixed-SOC EIS state.")


def _get_last_state(solution):
    cycles = getattr(solution, "cycles", None)
    if cycles:
        return cycles[-1].last_state
    return solution.last_state


def format_eis_state_label(mode, target_soc):
    """Return a human-readable description of the EIS measurement state."""
    if mode == "fixed_soc":
        return f"fixed SOC={target_soc:.0%} after recharge/rest"
    if mode == "cycle_end":
        return "post-discharge rest (near 0% SOC)"
    raise ValueError(f"Unsupported lifecycle EIS measurement mode: {mode}")


def build_lifecycle_soh_table(cycle_solutions):
    """Build a per-cycle SOH table from saved cycle solutions."""
    if not cycle_solutions:
        return pd.DataFrame(columns=["cycle", "discharge_capacity_ah", "soh_pct"])

    discharge_caps = np.array([_get_cycle_discharge_capacity_ah(cycle) for cycle in cycle_solutions], dtype=float)
    base_capacity = discharge_caps[0]
    soh_pct = discharge_caps / base_capacity * 100

    rows = []
    for cycle_number, (cycle_solution, discharge_capacity, soh_value) in enumerate(
        zip(cycle_solutions, discharge_caps, soh_pct),
        start=1,
    ):
        degradation = snapshot_degradation_variables(cycle_solution)
        rows.append(
            {
                "cycle": cycle_number,
                "discharge_capacity_ah": float(discharge_capacity),
                "soh_pct": float(soh_value),
                **degradation,
            }
        )
    return pd.DataFrame(rows)


def pick_soh_checkpoints(soh_table, target_levels, min_gap_pct=0.5):
    """Pick the closest unique checkpoints to the requested SOH milestones."""
    if soh_table.empty:
        return pd.DataFrame(columns=["cycle", "target_soh_pct", "soh_pct", "label"])

    selections = []
    used_indices = set()

    for target in target_levels:
        ordered_indices = (soh_table["soh_pct"] - target).abs().sort_values().index.tolist()
        chosen_idx = next((idx for idx in ordered_indices if idx not in used_indices), None)
        if chosen_idx is None:
            continue
        used_indices.add(chosen_idx)
        record = soh_table.loc[chosen_idx].to_dict()
        record["target_soh_pct"] = float(target)
        selections.append(record)

    min_idx = int(soh_table["soh_pct"].idxmin())
    min_soh = float(soh_table.loc[min_idx, "soh_pct"])
    if min_idx not in used_indices and all(abs(min_soh - item["soh_pct"]) >= min_gap_pct for item in selections):
        record = soh_table.loc[min_idx].to_dict()
        record["target_soh_pct"] = min_soh
        selections.append(record)

    checkpoints = pd.DataFrame(selections)
    if checkpoints.empty:
        return pd.DataFrame(columns=["cycle", "target_soh_pct", "soh_pct", "label"])

    checkpoints = checkpoints.sort_values("soh_pct", ascending=False).reset_index(drop=True)
    checkpoints["label"] = checkpoints.apply(
        lambda row: f"SOH={row['soh_pct']:.1f}% | Cycle {int(row['cycle'])}",
        axis=1,
    )
    return checkpoints


def prepare_eis_measurement_state(
    cycle_solution,
    get_hithium_params,
    model_options,
    var_pts,
    measurement_mode="fixed_soc",
    target_soc=0.5,
    temperature_k=298.15,
    rest_minutes=30,
    conditioning_period_minutes=1,
    double_layer_capacity=0.2,
    solver_rtol=1e-4,
    solver_atol=1e-6,
):
    """Prepare the battery state used for EIS at a lifecycle checkpoint."""
    state_label = format_eis_state_label(measurement_mode, target_soc)

    if measurement_mode == "cycle_end":
        return cycle_solution.last_state, {
            "eis_state": state_label,
            "eis_target_soc_pct": np.nan,
            "conditioning_charge_current_a": np.nan,
            "conditioning_duration_h": 0.0,
        }

    if measurement_mode != "fixed_soc":
        raise ValueError(f"Unsupported lifecycle EIS measurement mode: {measurement_mode}")
    if not 0 <= target_soc <= 1:
        raise ValueError("target_soc must be between 0 and 1.")
    if target_soc == 0:
        return cycle_solution.last_state, {
            "eis_state": state_label,
            "eis_target_soc_pct": 0.0,
            "conditioning_charge_current_a": 0.0,
            "conditioning_duration_h": 0.0,
        }

    discharge_capacity_ah = _get_cycle_discharge_capacity_ah(cycle_solution)
    charge_current_a = _get_cycle_charge_current_a(cycle_solution)
    conditioning_duration_h = target_soc * discharge_capacity_ah / charge_current_a

    conditioning_params = _build_parameter_values(
        get_hithium_params,
        1,
        temperature_k,
        double_layer_capacity,
    )
    conditioning_model = pybamm.lithium_ion.DFN(options=model_options)
    conditioning_experiment = pybamm.Experiment(
        [
            (
                f"Charge at {charge_current_a:.6f} A for {conditioning_duration_h:.6f} hours "
                f"({conditioning_period_minutes:g} minute period)",
                f"Rest for {rest_minutes:g} minutes ({conditioning_period_minutes:g} minute period)",
            )
        ],
        temperature=temperature_k,
    )
    conditioning_solution = pybamm.Simulation(
        conditioning_model,
        parameter_values=conditioning_params,
        experiment=conditioning_experiment,
        solver=pybamm.IDAKLUSolver(rtol=solver_rtol, atol=solver_atol),
        var_pts=var_pts,
    ).solve(
        starting_solution=cycle_solution.last_state,
        calc_esoh=False,
        showprogress=False,
    )

    prepared_state = _get_last_state(conditioning_solution)
    return prepared_state, {
        "eis_state": state_label,
        "eis_target_soc_pct": target_soc * 100,
        "conditioning_charge_current_a": charge_current_a,
        "conditioning_duration_h": conditioning_duration_h,
    }


def run_eis_from_checkpoint(
    cycle_solution,
    frequencies,
    get_hithium_params,
    model_options,
    var_pts,
    measurement_mode="fixed_soc",
    target_soc=0.5,
    temperature_k=298.15,
    rest_minutes=30,
    conditioning_period_minutes=1,
    double_layer_capacity=0.2,
    solver_rtol=1e-4,
    solver_atol=1e-6,
):
    """Run EIS from a saved lifecycle checkpoint state."""
    prepared_state, measurement_meta = prepare_eis_measurement_state(
        cycle_solution,
        get_hithium_params,
        model_options,
        var_pts,
        measurement_mode=measurement_mode,
        target_soc=target_soc,
        temperature_k=temperature_k,
        rest_minutes=rest_minutes,
        conditioning_period_minutes=conditioning_period_minutes,
        double_layer_capacity=double_layer_capacity,
        solver_rtol=solver_rtol,
        solver_atol=solver_atol,
    )

    eis_model = pybamm.lithium_ion.DFN(options=model_options)
    eis_model.set_initial_conditions_from(prepared_state, inplace=True)
    eis_params = _build_parameter_values(get_hithium_params, 1, temperature_k, double_layer_capacity)
    eis_sim = pybamm.EISSimulation(
        eis_model,
        parameter_values=eis_params,
        var_pts=var_pts,
    )
    return eis_sim.solve(frequencies), measurement_meta


def impedance_to_frame(solution, label, soh_pct, cycle_number):
    """Convert an EIS solution to a tidy dataframe."""
    frequencies = np.asarray(solution.frequencies, dtype=float)
    impedance = np.asarray(solution.impedance, dtype=complex)
    return pd.DataFrame(
        {
            "label": label,
            "cycle": cycle_number,
            "soh_pct": soh_pct,
            "frequency_hz": frequencies,
            "z_real_ohm": impedance.real,
            "z_imag_ohm": impedance.imag,
            "minus_z_im_ohm": -impedance.imag,
            "z_magnitude_ohm": np.abs(impedance),
            "phase_deg": np.degrees(np.angle(impedance)),
        }
    )


def summarize_impedance_components(solution, label, soh_pct, cycle_number):
    """Extract compact Nyquist features from an EIS solution."""
    frequencies = np.asarray(solution.frequencies, dtype=float)
    impedance = np.asarray(solution.impedance, dtype=complex)
    z_real = impedance.real
    z_imag = impedance.imag

    hf_idx = int(np.argmax(frequencies))
    lf_idx = int(np.argmin(frequencies))
    imag_peak_idx = int(np.argmax(-z_imag))
    semicircle_resolved = 0 < imag_peak_idx < len(frequencies) - 1

    r_ohm = max(float(z_real[hf_idx]), 0.0)
    r_polarization = max(float(z_real[lf_idx] - z_real[hf_idx]), 0.0)
    if semicircle_resolved:
        r_ct_proxy = min(max(float(2 * (z_real[imag_peak_idx] - z_real[hf_idx])), 0.0), r_polarization)
    else:
        r_ct_proxy = 0.0

    r_diffusion_proxy = max(r_polarization - r_ct_proxy, 0.0)
    imag_peak_frequency_hz = float(frequencies[imag_peak_idx])
    imag_peak_time_constant_s = 1 / (2 * np.pi * imag_peak_frequency_hz)
    nearest_1hz_idx = int(np.argmin(np.abs(np.log10(frequencies) - np.log10(1.0))))

    return {
        "label": label,
        "cycle": cycle_number,
        "soh_pct": float(soh_pct),
        "semicircle_resolved": bool(semicircle_resolved),
        "r_ohm_ohm": r_ohm,
        "r_polarization_ohm": r_polarization,
        "r_ct_proxy_ohm": r_ct_proxy,
        "r_diffusion_proxy_ohm": r_diffusion_proxy,
        "imag_peak_frequency_hz": imag_peak_frequency_hz,
        "imag_peak_time_constant_s": imag_peak_time_constant_s,
        "z_real_at_1hz_ohm": float(z_real[nearest_1hz_idx]),
        "minus_z_imag_at_1hz_ohm": float(-z_imag[nearest_1hz_idx]),
        "z_magnitude_at_1hz_ohm": float(np.abs(impedance[nearest_1hz_idx])),
        "phase_at_1hz_deg": float(np.degrees(np.angle(impedance[nearest_1hz_idx]))),
    }


def extract_frequency_slices(impedance_df, target_frequencies_hz):
    """Extract the nearest impedance rows for a small set of target frequencies."""
    rows = []
    for label, frame in impedance_df.groupby("label", sort=False):
        frequencies = frame["frequency_hz"].to_numpy(dtype=float)
        for target in target_frequencies_hz:
            idx = int(np.argmin(np.abs(np.log10(frequencies) - np.log10(target))))
            row = frame.iloc[idx]
            rows.append(
                {
                    "label": label,
                    "cycle": int(row["cycle"]),
                    "soh_pct": float(row["soh_pct"]),
                    "target_frequency_hz": float(target),
                    "nearest_frequency_hz": float(row["frequency_hz"]),
                    "z_real_ohm": float(row["z_real_ohm"]),
                    "minus_z_im_ohm": float(row["minus_z_im_ohm"]),
                    "z_magnitude_ohm": float(row["z_magnitude_ohm"]),
                    "phase_deg": float(row["phase_deg"]),
                }
            )
    return pd.DataFrame(rows)


def run_lifecycle_eis_study(
    *,
    get_hithium_params,
    frequencies,
    target_soh_levels,
    aging_cycles,
    aging_power_rate,
    var_pts,
    temperature_k=298.15,
    aging_t_factor=1,
    reference_voltage_v=3.2,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.5,
    measurement_mode="fixed_soc",
    target_soc=0.5,
    rest_minutes=30,
    period_minutes=10,
    conditioning_period_minutes=1,
    double_layer_capacity=0.2,
    model_options=None,
    solver_rtol=1e-4,
    solver_atol=1e-6,
):
    """Run lifecycle aging and EIS post-processing in one library call."""
    frequencies = np.asarray(frequencies, dtype=float)
    if np.any(frequencies <= 0):
        raise ValueError("frequencies must be positive.")

    resolved_model_options = dict(DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS if model_options is None else model_options)
    nominal_params = _build_parameter_values(get_hithium_params, 1, temperature_k, double_layer_capacity)
    nominal_capacity_ah = float(nominal_params["Nominal cell capacity [A.h]"])
    aging_power_w = aging_power_rate * nominal_capacity_ah * reference_voltage_v

    aging_params = _build_parameter_values(get_hithium_params, aging_t_factor, temperature_k, double_layer_capacity)
    aging_model = pybamm.lithium_ion.DFN(options=resolved_model_options)
    aging_experiment = build_lifecycle_power_experiment(
        aging_cycles,
        aging_power_w,
        nominal_capacity_ah,
        temperature_k,
        charge_cutoff_v=charge_cutoff_v,
        discharge_cutoff_v=discharge_cutoff_v,
        rest_minutes=rest_minutes,
        period_minutes=period_minutes,
        reference_voltage_v=reference_voltage_v,
    )
    aging_solver = pybamm.IDAKLUSolver(rtol=solver_rtol, atol=solver_atol)
    lifecycle_sim = pybamm.Simulation(
        aging_model,
        parameter_values=aging_params,
        experiment=aging_experiment,
        solver=aging_solver,
        var_pts=var_pts,
    )
    lifecycle_solution = lifecycle_sim.solve(
        calc_esoh=False,
        save_at_cycles=1,
        showprogress=False,
    )

    lifecycle_soh_df = build_lifecycle_soh_table(lifecycle_solution.cycles)
    lifecycle_checkpoints_df = pick_soh_checkpoints(lifecycle_soh_df, target_soh_levels)
    measurement_state_label = format_eis_state_label(measurement_mode, target_soc)

    lifecycle_eis_solutions = {}
    impedance_frames = []
    component_rows = []
    checkpoint_measurement_rows = []

    for _, row in lifecycle_checkpoints_df.iterrows():
        cycle_number = int(row["cycle"])
        cycle_solution = lifecycle_solution.cycles[cycle_number - 1]
        eis_solution, measurement_meta = run_eis_from_checkpoint(
            cycle_solution,
            frequencies,
            get_hithium_params,
            resolved_model_options,
            var_pts,
            measurement_mode=measurement_mode,
            target_soc=target_soc,
            temperature_k=temperature_k,
            rest_minutes=rest_minutes,
            conditioning_period_minutes=conditioning_period_minutes,
            double_layer_capacity=double_layer_capacity,
            solver_rtol=solver_rtol,
            solver_atol=solver_atol,
        )
        lifecycle_eis_solutions[row["label"]] = eis_solution
        impedance_frames.append(
            impedance_to_frame(
                eis_solution,
                label=row["label"],
                soh_pct=float(row["soh_pct"]),
                cycle_number=cycle_number,
            )
        )
        component_rows.append(
            summarize_impedance_components(
                eis_solution,
                label=row["label"],
                soh_pct=float(row["soh_pct"]),
                cycle_number=cycle_number,
            )
        )
        checkpoint_measurement_rows.append(
            {
                "cycle": cycle_number,
                **measurement_meta,
            }
        )

    lifecycle_impedance_df = pd.concat(impedance_frames, ignore_index=True) if impedance_frames else pd.DataFrame()
    lifecycle_components_df = pd.DataFrame(component_rows)
    if not lifecycle_components_df.empty:
        lifecycle_components_df = lifecycle_components_df.sort_values("soh_pct", ascending=False).reset_index(drop=True)

    measurement_meta_df = pd.DataFrame(checkpoint_measurement_rows)
    if not measurement_meta_df.empty:
        lifecycle_checkpoints_df = lifecycle_checkpoints_df.merge(measurement_meta_df, on="cycle", how="left")

    lifecycle_checkpoints_df["aging_power_w"] = aging_power_w
    return {
        "solution": lifecycle_solution,
        "soh_df": lifecycle_soh_df,
        "checkpoints_df": lifecycle_checkpoints_df,
        "impedance_df": lifecycle_impedance_df,
        "components_df": lifecycle_components_df,
        "eis_solutions": lifecycle_eis_solutions,
        "aging_power_w": aging_power_w,
        "measurement_state_label": measurement_state_label,
    }


__all__ = [
    "DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS",
    "build_lifecycle_power_experiment",
    "format_eis_state_label",
    "build_lifecycle_soh_table",
    "pick_soh_checkpoints",
    "prepare_eis_measurement_state",
    "run_eis_from_checkpoint",
    "impedance_to_frame",
    "summarize_impedance_components",
    "extract_frequency_slices",
    "run_lifecycle_eis_study",
]