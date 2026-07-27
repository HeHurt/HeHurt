"""data_registry 的单元测试：工况推断、scan 合并语义、过滤查询。"""

import json

import pytest

from src.data_registry import (
    curate_entry,
    filter_entries,
    infer_rate,
    infer_temperature,
    infer_test_type,
    load_registry,
    query_datasets,
    scan,
)


def test_infer_temperature_strong_and_weak():
    assert infer_temperature(["25℃-0.5P.csv"]) == 25
    assert infer_temperature(["-20℃循环.xlsx"]) == -20
    assert infer_temperature(["cw391_cw511_25C_0p25P.csv"]) == 25
    # 0.250C 是倍率，不应误判为温度
    assert infer_temperature(["Step10_Charge_0.250C.csv"]) is None
    # 文件名优先于上层目录
    assert infer_temperature(["A面_0.txt", "25℃0.5CP_0", "45℃&5并联效"]) == 25


def test_infer_rate_variants():
    assert infer_rate(["25℃-0.5P.csv"]) == "0.5P"
    assert infer_rate(["MIC_1175Ah_0p25P_cycle_life.dat"]) == "0.25P"
    assert infer_rate(["Step10_Charge_0.250C.csv"]) == "0.25C"
    assert infer_rate(["25℃0.5CP_0"]) == "0.5CP"
    assert infer_rate(["1P.dat"]) == "1P"
    assert infer_rate(["记录.txt"]) is None


def test_infer_test_type():
    assert infer_test_type("data_raw/MIC/倍率充电/0℃/x.xlsx") == "倍率充电"
    assert infer_test_type("data_raw/314Ah/Age/0.25P.dat") == "循环"
    assert infer_test_type("Hithium_TI_DCR @ Various Temp.xlsx") == "DCR"
    assert infer_test_type("Cell Pulse Mapping_20260410.xlsx") == "脉冲"
    assert infer_test_type("data_raw/280Ah/Exp/Sim_CC.csv") is None


def _make_tree(root):
    d = root / "data_raw" / "MIC_1175Ah" / "倍率充电" / "25℃"
    d.mkdir(parents=True)
    (d / "样品_No2#_SOH100%_倍率充电_20250310.csv").write_text("cycle,cap\n1,1175\n", encoding="utf-8")
    d2 = root / "data_processed" / "587Ah"
    d2.mkdir(parents=True)
    (d2 / "45℃-0.5P.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    # 非数据文件不登记
    (d2 / "plot.png").write_bytes(b"\x89PNG")


def test_scan_registers_and_infers(tmp_path):
    _make_tree(tmp_path)
    reg = scan(root=tmp_path)
    assert len(reg["entries"]) == 2
    by_cell = {e["cell"]: e for e in reg["entries"]}
    mic = by_cell["MIC_1175Ah"]
    assert mic["kind"] == "raw"
    assert mic["temperature_C"] == 25
    assert mic["test_type"] == "倍率充电"
    assert mic["soh_pct"] == 100
    assert mic["sample_id"] == "No2#"
    assert by_cell["587Ah"]["kind"] == "processed"
    assert by_cell["587Ah"]["rate"] == "0.5P"


def test_rescan_preserves_manual_fields_and_marks_missing(tmp_path):
    _make_tree(tmp_path)
    reg_path = tmp_path / "datasets.json"
    scan(root=tmp_path)

    # 人工修订：curated 条目 + auto 条目的人工字段
    reg = load_registry(reg_path)
    for e in reg["entries"]:
        if e["cell"] == "MIC_1175Ah":
            e["status"] = "curated"
            e["temperature_C"] = 26.5  # 人工纠正，curated 后重扫不得覆盖
        else:
            e["signals"] = ["capacity"]
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False)

    # 删除 processed 文件后重扫
    (tmp_path / "data_processed" / "587Ah" / "45℃-0.5P.csv").unlink()
    reg2 = scan(root=tmp_path)
    by_cell = {e["cell"]: e for e in reg2["entries"]}
    assert by_cell["MIC_1175Ah"]["status"] == "curated"
    assert by_cell["MIC_1175Ah"]["temperature_C"] == 26.5
    assert by_cell["587Ah"]["status"] == "missing"
    assert by_cell["587Ah"]["signals"] == ["capacity"]


def test_filter_entries():
    entries = [
        {"path": "a", "cell": "MIC_1175Ah", "temperature_C": 25.0, "rate": "0.5P",
         "test_type": "循环", "kind": "raw", "format": "csv", "status": "auto"},
        {"path": "b", "cell": "314Ah", "temperature_C": 45.0, "rate": None,
         "test_type": None, "kind": "processed", "format": "xlsx", "status": "auto"},
    ]
    assert len(filter_entries(entries, cell="mic")) == 1
    assert len(filter_entries(entries, temp=45.0)) == 1
    assert len(filter_entries(entries, rate="0.5p")) == 1
    assert len(filter_entries(entries, test="循环")) == 1
    assert len(filter_entries(entries, kind="processed")) == 1
    assert len(filter_entries(entries, fmt=".CSV")) == 1
    assert len(filter_entries(entries)) == 2


def test_query_datasets_resolves_paths_and_requires_unique(tmp_path):
    _make_tree(tmp_path)
    scan(root=tmp_path)
    hits = query_datasets(root=tmp_path, cell="MIC", temp=25, test="倍率充电")
    assert len(hits) == 1
    assert hits[0]["absolute_path"].endswith(".csv")
    assert query_datasets(root=tmp_path, cell="missing") == []
    with pytest.raises(ValueError, match="exactly one match"):
        query_datasets(root=tmp_path, require_unique=True)


def test_curate_entry_updates_metadata_and_survives_rescan(tmp_path):
    _make_tree(tmp_path)
    registry_path = tmp_path / "datasets.json"
    registry = scan(root=tmp_path, registry_path=registry_path)
    target = next(entry for entry in registry["entries"] if entry["cell"] == "MIC_1175Ah")
    curated = curate_entry(
        registry_path,
        entry_id_value=target["id"],
        temperature_C=26.5,
        signals=["voltage", "current", "capacity"],
        source="实验室A",
        quality="checked",
        status="curated",
    )
    assert curated["temperature_C"] == 26.5
    assert curated["status"] == "curated"
    rescanned = scan(root=tmp_path, registry_path=registry_path)
    saved = next(entry for entry in rescanned["entries"] if entry["id"] == target["id"])
    assert saved["temperature_C"] == 26.5
    assert saved["signals"] == ["voltage", "current", "capacity"]
    with pytest.raises(ValueError, match="exactly one"):
        curate_entry(registry_path, entry_id_value=target["id"], entry_path=target["path"])
