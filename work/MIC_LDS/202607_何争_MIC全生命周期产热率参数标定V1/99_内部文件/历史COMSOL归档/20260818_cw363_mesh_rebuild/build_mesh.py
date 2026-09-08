import json
import time
from collections import Counter
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260818_cw363_mesh_rebuild")
SOURCE = Path(r"D:\Users\hez\Desktop\mic\长时储能CW363-极片增高对能效差异_CW363设计参数.mph")
OUTPUT = Path(r"D:\Users\hez\Desktop\mic\长时储能CW363-极片增高对能效差异_CW363设计参数_网格修复.mph")
RESULT = RUN / "mesh_build_result.json"
ATTEMPTS_RESULT = RUN / "mesh_strategy_attempts.json"
RUN_LOG = RUN / "run.log"
ERROR_REPORT = RUN / "error_report.txt"
BUILD_TAG = "cw363_mesh_build"
VERIFY_TAG = "cw363_mesh_verify"
VOLUME_TYPES = ("tet", "prism", "hex", "pyr")


def tags(manager):
    return [str(value) for value in manager.tags()]


def mesh_stats(mesh):
    kinds = tags(mesh) if False else [str(value) for value in mesh.getTypes()]
    stats = {
        "is_empty": bool(mesh.isEmpty()),
        "is_complete": bool(mesh.isComplete()),
        "has_problems": bool(mesh.hasProblems()),
        "problems": [str(value) for value in mesh.problems()],
        "elements": int(mesh.getNumElem()),
        "vertices": int(mesh.getNumVertex()),
        "types": {},
        "volume_domain_counts": {str(domain): 0 for domain in range(1, 10)},
    }
    for kind in kinds:
        stats["types"][kind] = {
            "count": int(mesh.getNumElem(kind)),
            "min_quality": float(mesh.getMinQuality(kind)),
            "mean_quality": float(mesh.getMeanQuality(kind)),
        }
        if kind in VOLUME_TYPES:
            counts = Counter(int(value) for value in mesh.getElemEntity(kind))
            for domain in range(1, 10):
                stats["volume_domain_counts"][str(domain)] += int(counts.get(domain, 0))
    volume_qualities = [
        values["min_quality"]
        for kind, values in stats["types"].items()
        if kind in VOLUME_TYPES and values["count"] > 0
    ]
    stats["minimum_volume_quality"] = min(volume_qualities) if volume_qualities else None
    stats["all_domains_meshed"] = all(
        count > 0 for count in stats["volume_domain_counts"].values()
    )
    return stats


def remove_empty_tail(mesh):
    manager = mesh.feature()
    for tag in ("swe3", "ftri3"):
        if tag in tags(manager):
            manager.remove(tag)


def build_mapped_sweep(model):
    mesh = model.component("comp1").mesh("mesh1")
    manager = mesh.feature()
    remove_empty_tail(mesh)
    mesh.feature("ftri1").active(False)
    if "map1" in tags(manager):
        manager.remove("map1")
    mapped = manager.create("map1", "Map")
    mapped.label("主体映射四边形网格")
    mapped.selection().geom("geom1", 2)
    mapped.selection().set([1])

    distribution_1 = mapped.feature().create("dis1", "Distribution")
    distribution_1.selection().geom("geom1", 1)
    distribution_1.selection().set([2, 4])
    distribution_1.set("numelem", "15")

    distribution_2 = mapped.feature().create("dis2", "Distribution")
    distribution_2.selection().geom("geom1", 1)
    distribution_2.selection().set([1, 6])
    distribution_2.set("numelem", "20")

    manager.move("map1", 2)
    order = tags(manager)
    if order.index("map1") > order.index("swe1"):
        raise RuntimeError(f"map1 未能移动到 swe1 之前: {order}")
    mesh.run()
    return mesh, {"strategy": "mapped_quad_plus_sweep", "feature_order": order}


def build_refined_tri_sweep(model):
    mesh = model.component("comp1").mesh("mesh1")
    remove_empty_tail(mesh)
    size = mesh.feature("ftri1").feature("size1")
    size.set("custom", "on")
    size.set("hmaxactive", "on")
    size.set("hminactive", "on")
    size.set("hmax", "15[mm]")
    size.set("hmin", "2[mm]")
    size.set("hgradactive", "on")
    size.set("hgrad", "1.3")
    mesh.run()
    return mesh, {
        "strategy": "refined_free_triangle_plus_sweep",
        "hmax": "15[mm]",
        "hmin": "2[mm]",
    }


def load_clean(tag):
    try:
        ModelUtil.remove(tag)
    except Exception:
        pass
    return ModelUtil.load(tag, str(SOURCE))


def accepted(stats, strategy):
    if stats["is_empty"] or not stats["is_complete"] or not stats["all_domains_meshed"]:
        return False
    if strategy == "mapped_quad_plus_sweep":
        return (
            stats["types"].get("hex", {}).get("count", 0) > 0
            and stats["types"].get("prism", {}).get("count", 0) > 0
        )
    quality = stats["minimum_volume_quality"]
    return quality is not None and quality >= 0.002764


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"输出文件已存在，拒绝覆盖: {OUTPUT}")
    source_before = SOURCE.stat()
    attempts = []
    selected = None
    started = time.time()

    model = load_clean(BUILD_TAG)
    try:
        try:
            mesh, detail = build_mapped_sweep(model)
            stats = mesh_stats(mesh)
            attempts.append({**detail, "ok": True, "stats": stats})
            if accepted(stats, detail["strategy"]):
                selected = {**detail, "stats": stats}
                model.save(str(OUTPUT))
        except Exception as exc:
            attempts.append({"strategy": "mapped_quad_plus_sweep", "ok": False, "error": str(exc)})
    finally:
        ModelUtil.remove(BUILD_TAG)

    ATTEMPTS_RESULT.write_text(
        json.dumps({"attempts": attempts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if selected is None:
        model = load_clean(BUILD_TAG)
        try:
            mesh, detail = build_refined_tri_sweep(model)
            stats = mesh_stats(mesh)
            attempts.append({**detail, "ok": True, "stats": stats})
            ATTEMPTS_RESULT.write_text(
                json.dumps({"attempts": attempts}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if not accepted(stats, detail["strategy"]):
                raise RuntimeError(f"备用网格未达到完整性或质量门槛: {stats}")
            selected = {**detail, "stats": stats}
            model.save(str(OUTPUT))
        finally:
            ModelUtil.remove(BUILD_TAG)

    verified = ModelUtil.load(VERIFY_TAG, str(OUTPUT))
    try:
        mesh = verified.component("comp1").mesh("mesh1")
        if mesh.isEmpty() or not mesh.isComplete():
            mesh.run()
        verification = mesh_stats(mesh)
        feature_tags = tags(mesh.feature())
        verification["empty_tail_removed"] = "ftri3" not in feature_tags and "swe3" not in feature_tags
        verification["feature_tags"] = feature_tags
        if not verification["is_complete"] or not verification["all_domains_meshed"]:
            raise AssertionError(f"重载后网格覆盖断言失败: {verification}")
        if not verification["empty_tail_removed"]:
            raise AssertionError(f"空网格节点仍存在: {feature_tags}")
    finally:
        ModelUtil.remove(VERIFY_TAG)

    source_after = SOURCE.stat()
    payload = {
        "source": str(SOURCE),
        "output_model": str(OUTPUT),
        "source_unchanged": (
            source_before.st_size == source_after.st_size
            and source_before.st_mtime_ns == source_after.st_mtime_ns
        ),
        "elapsed_s": time.time() - started,
        "attempts": attempts,
        "selected": selected,
        "verification_after_reload": verification,
        "solve_run": False,
    }
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    RUN_LOG.write_text(
        "mesh_build=success\nreload_verify=success\nall_domains_meshed=true\nsolve_run=false\n",
        encoding="utf-8",
    )
    ERROR_REPORT.write_text("", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(OUTPUT), "result": str(RESULT)}, ensure_ascii=False))


try:
    main()
except Exception as exc:
    ERROR_REPORT.write_text(str(exc), encoding="utf-8")
    RUN_LOG.write_text(f"mesh_build=failed\nerror={exc}\n", encoding="utf-8")
    raise
