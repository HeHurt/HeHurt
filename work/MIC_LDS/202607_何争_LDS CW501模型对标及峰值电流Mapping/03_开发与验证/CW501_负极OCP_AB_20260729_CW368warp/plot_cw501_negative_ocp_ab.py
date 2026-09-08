from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

TASK_ROOT = Path(
    r"D:\Users\hez\Desktop\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW501模型对标及峰值电流Mapping"
)
BASELINE_DIR = TASK_ROOT / "04_输出结果" / "20260729_093615_full_v2"
AB_DIR = (
    TASK_ROOT
    / "03_开发与验证"
    / "CW501_负极OCP_AB_20260729_CW368warp"
)

baseline = pd.read_csv(BASELINE_DIR / "curves.csv", encoding="utf-8-sig")
candidate = pd.read_csv(AB_DIR / "curves.csv", encoding="utf-8-sig")

for temperature_c in [5, 25, 45]:
    rates = sorted(
        baseline.loc[
            baseline["temperature_c"] == temperature_c,
            "p_rate",
        ].unique()
    )
    fig, axes = plt.subplots(
        2,
        len(rates),
        figsize=(4.3 * len(rates), 7.2),
        squeeze=False,
    )
    for row, direction in enumerate(["充电", "放电"]):
        for col, p_rate in enumerate(rates):
            ax = axes[row, col]
            key = (
                np.isclose(baseline["temperature_c"], temperature_c)
                & (baseline["direction"] == direction)
                & np.isclose(baseline["p_rate"], p_rate)
            )
            base_case = baseline[key]
            candidate_case = candidate[
                np.isclose(candidate["temperature_c"], temperature_c)
                & (candidate["direction"] == direction)
                & np.isclose(candidate["p_rate"], p_rate)
            ]
            for series, curve in base_case[
                base_case["series"].str.startswith("exp_")
            ].groupby("series"):
                ax.plot(
                    curve["capacity_ah"],
                    curve["voltage_v"],
                    color="#7F7F7F",
                    ls="--",
                    lw=0.9,
                    alpha=0.65,
                    label=series.replace("exp_", "Exp "),
                )
            base_sim = base_case[base_case["series"] == "dfn_sim"]
            new_sim = candidate_case[candidate_case["series"] == "dfn_sim"]
            ax.plot(
                base_sim["capacity_ah"],
                base_sim["voltage_v"],
                color="#111111",
                lw=1.6,
                label="Baseline OCP",
            )
            ax.plot(
                new_sim["capacity_ah"],
                new_sim["voltage_v"],
                color="#D62728",
                lw=1.5,
                label="CW368-warp OCP",
            )
            ax.set_title(
                f"{temperature_c}℃ {p_rate:.3f}P "
                f"{'Charge' if direction == '充电' else 'Discharge'}"
            )
            ax.set_xlabel("Capacity [Ah]")
            ax.set_ylabel("Voltage [V]")
            ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    output_path = AB_DIR / f"cw501_negative_ocp_ab_{temperature_c}C.png"
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(output_path)
