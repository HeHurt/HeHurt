"""Utilities for building robust PyBaMM experiment steps."""


def estimate_power_step_duration_hours(
    power_w,
    nominal_capacity_ah,
    reference_voltage_v=3.2,
    safety_factor=1.25,
    min_duration_hours=2.0,
):
    """Estimate a conservative duration for a constant-power step."""
    power_w = abs(float(power_w))
    nominal_capacity_ah = float(nominal_capacity_ah)
    reference_voltage_v = float(reference_voltage_v)
    safety_factor = float(safety_factor)
    min_duration_hours = float(min_duration_hours)

    if power_w <= 0:
        raise ValueError("power_w must be positive")
    if nominal_capacity_ah <= 0:
        raise ValueError("nominal_capacity_ah must be positive")
    if reference_voltage_v <= 0:
        raise ValueError("reference_voltage_v must be positive")
    if safety_factor <= 0:
        raise ValueError("safety_factor must be positive")
    if min_duration_hours <= 0:
        raise ValueError("min_duration_hours must be positive")

    base_duration_hours = nominal_capacity_ah * reference_voltage_v / power_w
    return max(base_duration_hours * safety_factor, min_duration_hours)


def build_power_step(
    direction,
    power_w,
    cutoff_voltage_v,
    nominal_capacity_ah,
    period_minutes=0.5,
    reference_voltage_v=3.2,
    safety_factor=1.25,
    min_duration_hours=2.0,
    power_precision=2,
    duration_precision=1,
):
    """Build a PyBaMM experiment string with an explicit duration safeguard."""
    direction = str(direction).strip().capitalize()
    if direction not in {"Charge", "Discharge"}:
        raise ValueError("direction must be 'Charge' or 'Discharge'")

    cutoff_voltage_v = float(cutoff_voltage_v)
    period_minutes = float(period_minutes)
    if cutoff_voltage_v <= 0:
        raise ValueError("cutoff_voltage_v must be positive")
    if period_minutes <= 0:
        raise ValueError("period_minutes must be positive")

    duration_hours = estimate_power_step_duration_hours(
        power_w=power_w,
        nominal_capacity_ah=nominal_capacity_ah,
        reference_voltage_v=reference_voltage_v,
        safety_factor=safety_factor,
        min_duration_hours=min_duration_hours,
    )

    return (
        f"{direction} at {abs(float(power_w)):.{power_precision}f}W "
        f"for {duration_hours:.{duration_precision}f} hours or until "
        f"{cutoff_voltage_v:.2f} V ({period_minutes:.1f} minute period)"
    )
