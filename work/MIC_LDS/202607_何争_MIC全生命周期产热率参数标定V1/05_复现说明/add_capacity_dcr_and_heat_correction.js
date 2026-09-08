const fs = require("fs");

const notebookPath = process.argv[2];
const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));

function source(cell) {
  return (cell.source || []).join("");
}

function findCodeCell(marker) {
  const cell = notebook.cells.find(
    (item) => item.cell_type === "code" && source(item).includes(marker),
  );
  if (!cell) {
    throw new Error(`Cannot find code cell containing: ${marker}`);
  }
  return cell;
}

function replaceExact(text, from, to, label) {
  if (!text.includes(from)) {
    throw new Error(`Cannot find ${label}: ${from}`);
  }
  return text.replace(from, to);
}

const importsCell = findCodeCell("from src.notebook import setup_notebook");
let importsSource = source(importsCell);
importsSource = replaceExact(
  importsSource,
  "run_pulse_lifecycle_scenarios = simulation_module.run_pulse_lifecycle_scenarios\n",
  "run_pulse_lifecycle_scenarios = simulation_module.run_pulse_lifecycle_scenarios\n"
    + "perform_dcr_test = simulation_module.perform_dcr_test\n",
  "perform_dcr_test binding",
);
importsCell.source = importsSource.split(/(?<=\n)/);

const configCell = findCodeCell('RUN_MODE = "study"');
let configSource = source(configCell);
configSource = replaceExact(
  configSource,
  "HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT = 0.310139\n",
  [
    "HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT = 0.310139",
    "",
    "# 仅作用于中文Excel汇总/明细中的修正后总产热，以及最终产热图。",
    "# 公式：修正后产热功率 = 原始总产热功率 * HEAT_EXPORT_SCALE + HEAT_EXPORT_OFFSET_W",
    "HEAT_EXPORT_SCALE = 1.0",
    "HEAT_EXPORT_OFFSET_W = 0.0",
    "",
    "DCR_TARGET_SOC = 0.50",
    "DCR_CHARGE_C_RATE = 0.25",
    "DCR_PULSE_C_RATE = 1.0",
    "DCR_PULSE_DURATION_S = 30.0",
    "EXP_CAPACITY_DCR_FILE = (",
    '    WORKSPACE_ROOT / "work" / "MIC_LDS"',
    '    / "202607_何争_MIC全生命周期产热率参数标定V1"',
    '    / "03_输入数据" / "MIC_25C_0p25P容量_DCR对标点.csv"',
    ")",
    "",
  ].join("\n"),
  "heat correction and DCR config",
);
configCell.source = configSource.split(/(?<=\n)/);

const postprocessIndex = notebook.cells.findIndex(
  (item) => item.cell_type === "markdown" && source(item).includes("## 4. 中文 Excel 与图表"),
);
if (postprocessIndex < 0) {
  throw new Error("Cannot find Chinese Excel section");
}

const comparisonMarkdown = {
  cell_type: "markdown",
  metadata: {},
  source: [
    "## 4. 全生命周期容量与DCR对标\n",
    "\n",
    "容量使用老化主线每50等效圈实际点；DCR在各SOH检查点关闭老化后执行50% SOC、1C-30s脉冲。\n",
    "实测点来自任务输入目录。DCR诊断结果按参数指纹保存，参数变化后不会复用旧结果。\n",
  ],
};

const comparisonCode = String.raw`perform_dcr_test = simulation_module.perform_dcr_test


def build_parameter_values(contact_resistance_ohm, temperature_k):
    values = pybamm.ParameterValues("OKane2022")
    values.update(
        make_parameter_loader(contact_resistance_ohm)(1, temperature=temperature_k),
        check_already_exists=False,
    )
    return values


def latest_positive_capacity_ah(solution):
    cycle = list(getattr(solution, "cycles", []))[-1]
    capacities = []
    for step in getattr(cycle, "steps", []):
        current = np.asarray(step["Current [A]"].entries, dtype=float)
        if current.size == 0 or np.nanmean(current) <= 0:
            continue
        throughput = np.asarray(step["Throughput capacity [A.h]"].entries, dtype=float)
        if throughput.size:
            capacities.append(abs(float(throughput[-1] - throughput[0])))
    return max(capacities) if capacities else np.nan


def dcr_checkpoint_path(resistance_mohm, temperature_c):
    stem = f"R{resistance_mohm:.5f}mOhm_T{temperature_c:g}C"
    return CHECKPOINT_DIR / f"{stem}_capacity_dcr_actual.csv"


def simulate_soh_checkpoint_dcr(bundle, resistance_mohm, temperature_c):
    rows = []
    diagnostic_items = [
        item for item in bundle["diagnostic_solutions"]
        if np.isclose(item["diagnostic_p_rate"], AGING_P_RATE)
    ]
    diagnostic_items.sort(key=lambda item: item["target_soh_pct"], reverse=True)
    model = pybamm.lithium_ion.DFN(MODEL_OPTIONS)
    solver = pybamm.IDAKLUSolver(rtol=SOLVER_RTOL, atol=SOLVER_ATOL)
    params = build_parameter_values(resistance_mohm * 1e-3, temperature_c + 273.15)
    for item in diagnostic_items:
        solution = item["solution"]
        capacity_ah = latest_positive_capacity_ah(solution)
        charge_time_h = capacity_ah / (NOMINAL_CAPACITY_AH * DCR_CHARGE_C_RATE)
        row = {
            "temperature_c": temperature_c,
            "target_soh_pct": item["target_soh_pct"],
            "actual_soh_pct": item["actual_soh_pct"],
            "real_cycle": item["real_cycle"],
            "capacity_ah": capacity_ah,
            "parameter_fingerprint": PARAMETER_FINGERPRINT,
            "data_source": "仿真实际点",
            "dcr_status": "simulated",
            "dcr_error": "",
        }
        try:
            result = perform_dcr_test(
                solution.last_state,
                params,
                model,
                solver,
                VAR_PTS,
                current=NOMINAL_CAPACITY_AH,
                C1=DCR_CHARGE_C_RATE,
                C2=DCR_PULSE_C_RATE,
                t=DCR_PULSE_DURATION_S,
                charge_time=charge_time_h,
                target_soc=DCR_TARGET_SOC,
            )
            row.update({
                "dcr_mean_mohm": result["dcr_mean"] * 1e3,
                "dcr_charge_mohm": result["dcr_charge"] * 1e3,
                "dcr_discharge_mohm": result["dcr_discharge"] * 1e3,
            })
        except Exception as exc:
            row.update({
                "dcr_mean_mohm": np.nan,
                "dcr_charge_mohm": np.nan,
                "dcr_discharge_mohm": np.nan,
                "dcr_status": "failed",
                "dcr_error": f"{type(exc).__name__}: {exc}",
            })
        rows.append(row)
    result_df = pd.DataFrame(rows)
    valid = result_df["dcr_mean_mohm"].dropna()
    baseline = float(valid.iloc[0]) if not valid.empty else np.nan
    result_df["dcr_growth_pct"] = (result_df["dcr_mean_mohm"] / baseline - 1.0) * 100.0
    return result_df


def load_or_simulate_dcr(bundle, resistance_mohm, temperature_c):
    path = dcr_checkpoint_path(resistance_mohm, temperature_c)
    if path.exists():
        cached = pd.read_csv(path)
        fingerprints = set(cached.get("parameter_fingerprint", pd.Series(dtype=str)).astype(str))
        if fingerprints == {PARAMETER_FINGERPRINT}:
            print("复用DCR检查点：", path)
            return cached
    if bundle is None:
        print("缺少内存中的老化状态，无法补做DCR诊断：", path.name)
        return pd.DataFrame()
    result_df = simulate_soh_checkpoint_dcr(bundle, resistance_mohm, temperature_c)
    result_df.to_csv(path, index=False, encoding="utf-8-sig")
    print("DCR检查点已保存：", path)
    return result_df


def append_dcr_trend_extrapolation(dcr_df, targets_pct):
    if dcr_df.empty:
        return dcr_df
    result = dcr_df.copy()
    last_actual_soh = float(result["actual_soh_pct"].min())
    missing = [float(target) for target in targets_pct if target < last_actual_soh]
    fit_df = result.sort_values("actual_soh_pct").head(min(5, len(result)))
    rows = []
    for target in missing:
        row = {
            "temperature_c": float(result["temperature_c"].iloc[0]),
            "target_soh_pct": target,
            "actual_soh_pct": target,
            "parameter_fingerprint": PARAMETER_FINGERPRINT,
            "data_source": "趋势外推",
            "dcr_status": "extrapolated",
            "dcr_error": "",
        }
        for column in [
            "real_cycle", "capacity_ah", "dcr_mean_mohm",
            "dcr_charge_mohm", "dcr_discharge_mohm", "dcr_growth_pct",
        ]:
            valid = fit_df[["actual_soh_pct", column]].dropna()
            if len(valid) < 2:
                row[column] = np.nan
                continue
            degree = min(2, len(valid) - 1)
            row[column] = float(np.polyval(
                np.polyfit(valid["actual_soh_pct"], valid[column], degree),
                target,
            ))
        rows.append(row)
    if rows:
        result = pd.concat([result, pd.DataFrame(rows)], ignore_index=True)
    return result.sort_values("target_soh_pct", ascending=False).reset_index(drop=True)


experimental_capacity_dcr = pd.read_csv(EXP_CAPACITY_DCR_FILE)
capacity_dcr_tables = {}
for resistance_mohm in CONTACT_RESISTANCE_CASES_MOHM:
    for temperature_c in AGING_TEMPERATURES_C:
        case_key = (resistance_mohm, temperature_c)
        bundle = case_bundles.get(case_key)
        paths = checkpoint_paths(resistance_mohm, temperature_c)
        if bundle is not None:
            main_df = bundle["main_df"].copy()
        elif paths["main"].exists():
            main_df = pd.read_csv(paths["main"])
        else:
            main_df = pd.DataFrame()
        if not main_df.empty:
            main_df = main_df.assign(
                temperature_c=temperature_c,
                contact_resistance_mohm=resistance_mohm,
                capacity_retention_pct=main_df["capacity_retention"] * 100.0,
                data_source="仿真实际点",
            )
        dcr_df = load_or_simulate_dcr(bundle, resistance_mohm, temperature_c)
        dcr_df = append_dcr_trend_extrapolation(dcr_df, SOH_TARGETS_PCT)
        capacity_dcr_tables[case_key] = {"capacity": main_df, "dcr": dcr_df}


RAW_TOTAL_COLUMNS = {
    "calibrated_total_charge_w": "raw_total_charge_w",
    "calibrated_total_discharge_w": "raw_total_discharge_w",
}
for case_key, table in case_tables.items():
    corrected = table.copy()
    for total_column, raw_column in RAW_TOTAL_COLUMNS.items():
        corrected[raw_column] = corrected[total_column]
        corrected[total_column] = (
            corrected[raw_column] * HEAT_EXPORT_SCALE + HEAT_EXPORT_OFFSET_W
        )
    case_tables[case_key] = corrected

HEAT_COLUMN_CN.update({
    "raw_total_charge_w": "充电修正前平均总产热功率(W)",
    "raw_total_discharge_w": "放电修正前平均总产热功率(W)",
    "calibrated_total_charge_w": "充电修正后平均总产热功率(W)",
    "calibrated_total_discharge_w": "放电修正后平均总产热功率(W)",
})

print(
    "产热导出修正：修正后 = 修正前 × "
    f"{HEAT_EXPORT_SCALE:g} + {HEAT_EXPORT_OFFSET_W:g} W"
)
`;

const comparisonCell = {
  cell_type: "code",
  execution_count: null,
  metadata: {},
  outputs: [],
  source: comparisonCode.split(/(?<=\n)/),
};

notebook.cells.splice(postprocessIndex, 0, comparisonMarkdown, comparisonCell);

const excelMarkdown = notebook.cells.find(
  (item) => item.cell_type === "markdown" && source(item).includes("## 4. 中文 Excel 与图表"),
);
excelMarkdown.source = [
  "## 5. 中文 Excel 与图表\n",
  "\n",
  "产热汇总和图表使用修正后总产热；分项表同时保留修正前与修正后总产热。\n",
  "容量和DCR不应用产热修正系数。\n",
];

const excelCell = findCodeCell("from openpyxl.styles import Alignment");
let excelSource = source(excelCell);
excelSource = replaceExact(
  excelSource,
  '        ["可逆热基准", ENTROPY_SOURCE_NOTE],\n',
  '        ["可逆热基准", ENTROPY_SOURCE_NOTE],\n'
    + '        ["产热导出修正公式", f"修正后=修正前×{HEAT_EXPORT_SCALE:g}+{HEAT_EXPORT_OFFSET_W:g}W"],\n',
  "Excel explanation correction row",
);
excelSource = replaceExact(
  excelSource,
  '        ["熵热文件", str(ENTROPY_CURVE_FILE)], ["熵热样本", ENTROPY_SAMPLE_LABEL],\n',
  '        ["熵热文件", str(ENTROPY_CURVE_FILE)], ["熵热样本", ENTROPY_SAMPLE_LABEL],\n'
    + '        ["产热导出乘数", HEAT_EXPORT_SCALE], ["产热导出偏置(W)", HEAT_EXPORT_OFFSET_W],\n'
    + '        ["DCR诊断", f"{DCR_TARGET_SOC*100:g}%SOC, {DCR_PULSE_C_RATE:g}C-{DCR_PULSE_DURATION_S:g}s"],\n',
  "Excel config correction rows",
);
excelSource = replaceExact(
  excelSource,
  '    detail_all = pd.concat(\n        [temperature_tables[temperature_c] for temperature_c in AGING_TEMPERATURES_C],\n        ignore_index=True,\n    )\n',
  '    detail_all = pd.concat(\n        [temperature_tables[temperature_c] for temperature_c in AGING_TEMPERATURES_C],\n        ignore_index=True,\n    )\n'
    + '    capacity_all = pd.concat(\n'
    + '        [capacity_dcr_tables[(resistance_mohm, temperature_c)]["capacity"]\n'
    + '         for temperature_c in AGING_TEMPERATURES_C],\n'
    + '        ignore_index=True,\n'
    + '    )\n'
    + '    dcr_all = pd.concat(\n'
    + '        [capacity_dcr_tables[(resistance_mohm, temperature_c)]["dcr"]\n'
    + '         for temperature_c in AGING_TEMPERATURES_C],\n'
    + '        ignore_index=True,\n'
    + '    )\n',
  "capacity DCR table assembly",
);
excelSource = replaceExact(
  excelSource,
  '        mechanism.to_excel(writer, sheet_name="老化机制", index=False)\n',
  '        mechanism.to_excel(writer, sheet_name="老化机制", index=False)\n'
    + '        capacity_all.rename(columns={\n'
    + '            "real_cycle": "等效循环圈数", "discharge_capacity_ah": "放电容量(Ah)",\n'
    + '            "capacity_retention_pct": "容量保持率(%)", "data_source": "数据来源",\n'
    + '        }).to_excel(writer, sheet_name="全生命周期容量", index=False)\n'
    + '        dcr_all.rename(columns={\n'
    + '            "target_soh_pct": "目标SOH(%)", "actual_soh_pct": "实际或外推SOH(%)",\n'
    + '            "real_cycle": "等效循环圈数", "capacity_ah": "诊断放电容量(Ah)",\n'
    + '            "dcr_mean_mohm": "平均DCR(mΩ)", "dcr_charge_mohm": "充电DCR(mΩ)",\n'
    + '            "dcr_discharge_mohm": "放电DCR(mΩ)", "dcr_growth_pct": "DCR增长率(%)",\n'
    + '            "data_source": "数据来源", "dcr_status": "DCR状态", "dcr_error": "DCR错误",\n'
    + '        }).to_excel(writer, sheet_name="全生命周期DCR", index=False)\n'
    + '        experimental_capacity_dcr.to_excel(writer, sheet_name="容量_DCR实测点", index=False)\n',
  "capacity DCR Excel sheets",
);
excelSource = replaceExact(
  excelSource,
  '    output_paths.append(workbook)\n',
  String.raw`    fig_compare, compare_axes = plt.subplots(1, 2, figsize=(11, 4.2))
    capacity_plot = capacity_all.loc[capacity_all["temperature_c"].eq(25.0)]
    compare_axes[0].plot(
        capacity_plot["real_cycle"], capacity_plot["capacity_retention_pct"],
        "-", color="#111111", label="仿真",
    )
    compare_axes[0].plot(
        experimental_capacity_dcr["循环圈数"], experimental_capacity_dcr["容量保持率(%)"],
        "o--", color="#d62728", label="实测",
    )
    compare_axes[0].set(
        xlabel="等效循环圈数", ylabel="容量保持率 (%)", title="全生命周期容量保持率",
    )

    dcr_plot = dcr_all.loc[dcr_all["temperature_c"].eq(25.0)].sort_values("real_cycle")
    dcr_actual = dcr_plot.loc[dcr_plot["data_source"].eq("仿真实际点")]
    dcr_extrapolated = dcr_plot.loc[dcr_plot["data_source"].eq("趋势外推")]
    compare_axes[1].plot(
        dcr_actual["real_cycle"], dcr_actual["dcr_growth_pct"],
        "o-", color="#111111", label="仿真",
    )
    if not dcr_extrapolated.empty:
        joined = pd.concat([dcr_actual.tail(1), dcr_extrapolated]).sort_values("real_cycle")
        compare_axes[1].plot(
            joined["real_cycle"], joined["dcr_growth_pct"],
            "x--", color="#111111", label="仿真外推",
        )
    compare_axes[1].plot(
        experimental_capacity_dcr["循环圈数"], experimental_capacity_dcr["DCR增长率(%)"],
        "o--", color="#d62728", label="实测",
    )
    compare_axes[1].set(
        xlabel="等效循环圈数", ylabel="DCR增长率 (%)", title="50%SOC 1C-30s DCR",
    )
    for axis in compare_axes:
        axis.grid(True, ls="--", alpha=0.35)
        axis.legend()
    fig_compare.tight_layout()
    compare_plot_path = OUTPUT_ROOT / (
        f"{CELL_NAME}_容量_DCR全生命周期对标_R{resistance_mohm:.5f}mΩ.png"
    )
    fig_compare.savefig(compare_plot_path, dpi=220, bbox_inches="tight")
    plt.show()

    output_paths.append(workbook)
`,
  "capacity DCR plot",
);
excelCell.source = excelSource.split(/(?<=\n)/);

fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");
console.log(`Updated notebook: ${notebookPath}`);
