from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_090000_coin_v7_local_porosity")
DATA = RUN / "exported_data"
PLOTS = RUN / "plots"
REGIONS = [("negative", "负极"), ("separator", "隔膜"), ("positive", "正极")]

try:
    import scienceplots  # noqa: F401
    plt.style.use(["science", "no-latex"])
except (ImportError, OSError):
    pass
plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

frames = {name: pd.read_csv(DATA / f"{name}_local_pressure_porosity_100N.csv") for name, _ in REGIONS}
fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.2), constrained_layout=True)
for column, (name, title) in enumerate(REGIONS):
    frame = frames[name]
    r = frame.r_um / 1000
    z = frame.z_um / 1000
    pressure = axes[0, column].scatter(r, z, c=frame.pressure_MPa, s=4, cmap="turbo", vmin=0, vmax=2)
    porosity = axes[1, column].scatter(r, z, c=frame.porosity, s=4, cmap="viridis")
    axes[0, column].set_title(f"{title}：局部压缩压力")
    axes[1, column].set_title(f"{title}：局部孔隙率")
    for row in range(2):
        axes[row, column].set_xlabel("径向位置 r (mm)")
        axes[row, column].set_ylabel("轴向位置 z (mm)")
        axes[row, column].set_aspect("equal", adjustable="box")
    fig.colorbar(pressure, ax=axes[0, column], label="MPa", shrink=0.8)
    fig.colorbar(porosity, ax=axes[1, column], label="孔隙率", shrink=0.8)
fig.suptitle("V7：100 N 下局部压力–孔隙率空间耦合验证", fontsize=14)
path = PLOTS / "local_pressure_porosity_100N.png"
fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(path)
