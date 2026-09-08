from pathlib import Path

import numpy as np
import pandas as pd

from BatteryProject.src.workflows import sodium_rate_benchmark as sodium


def _write_curve(path: Path, *, discharge: bool = False) -> None:
    capacity = np.array([0.0, 1.0, 2.0])
    if discharge:
        capacity = -capacity
    pd.DataFrame(
        {
            "TimeS": [0.0, 1.0, 2.0],
            "CurrA": [16.4 if discharge else -16.4] * 3,
            "VoltV": [2.0, 2.5, 3.0],
            "AccuCapAh": capacity,
        }
    ).to_csv(path, index=False)


def test_discover_sodium_rate_cases_maps_filename_metadata(tmp_path):
    charge_dir = tmp_path / "3_倍充数据-0324更新" / "25℃ 倍率充电"
    discharge_dir = tmp_path / "4_倍放数据-0324更新" / "-20℃ 倍率放电"
    charge_dir.mkdir(parents=True)
    discharge_dir.mkdir(parents=True)
    _write_curve(charge_dir / "Para-0.5C-Chrg—sample_wc_data.csv")
    _write_curve(discharge_dir / "Para-1.5C-DisChrg—sample_wc_data.csv", discharge=True)

    cases = sodium.discover_sodium_rate_cases(tmp_path)

    assert [case.key for case in cases] == [
        ("charge", 25.0, 0.5),
        ("discharge", -20.0, 1.5),
    ]


def test_load_sodium_rate_curve_normalizes_discharge_capacity(tmp_path):
    data_path = tmp_path / "Para-0.5C-DisChrg—sample_wc_data.csv"
    _write_curve(data_path, discharge=True)
    case = sodium.SodiumRateCase("discharge", 25.0, 0.5, data_path)

    curve = sodium.load_sodium_rate_curve(case)

    assert curve["capacity_ah"].tolist() == [0.0, 1.0, 2.0]


def test_run_sodium_rate_case_smoke(monkeypatch, tmp_path):
    data_path = tmp_path / "Para-0.1C-Chrg—sample_wc_data.csv"
    _write_curve(data_path)
    case = sodium.SodiumRateCase("charge", 25.0, 0.1, data_path)

    class FakeVariable:
        def __init__(self, entries):
            self.entries = np.asarray(entries, dtype=float)

    class FakeSolution:
        termination = "event: Voltage > 3.3 V"

        def __getitem__(self, name):
            values = {
                "Throughput capacity [A.h]": [0.0, 1.0, 2.0],
                "Voltage [V]": [2.0, 2.5, 3.0],
                "Current [A]": [-16.4, -16.4, -16.4],
                "Time [s]": [0.0, 1.0, 2.0],
            }
            return FakeVariable(values[name])

    class FakeParameters:
        def __init__(self, _name):
            self.values = {}

        def update(self, values, **_kwargs):
            self.values.update(values)

    class FakeSimulation:
        def __init__(self, *_args, **_kwargs):
            pass

        def solve(self, *, initial_soc, showprogress):
            assert initial_soc == 0.0
            assert showprogress is False
            return FakeSolution()

    monkeypatch.setattr(sodium.pybamm, "ParameterValues", FakeParameters)
    monkeypatch.setattr(sodium.pybamm, "Experiment", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(sodium.pybamm, "Simulation", FakeSimulation)
    monkeypatch.setattr(sodium.pybamm, "IDAKLUSolver", lambda: object())
    monkeypatch.setattr(sodium, "build_sodium_rate_model", lambda: object())

    result = sodium.run_sodium_rate_case(case, lambda *_args: {})

    assert result.status == "ok"
    assert result.metrics["voltage_rmse_v"] == 0.0
    assert result.metrics["capacity_error_ah"] == 0.0
