import json
from pathlib import Path


SOURCE = Path(r"E:\Downloads\coin_geometry.mph")
OUTPUT_MODEL = Path(r"E:\Downloads\coin_geometry_参数路径已切换.mph")
PARAM_DIR = Path(r"D:\Users\hez\Desktop\AI虚拟电芯\coin\params")
RESULT = Path(
    r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\path_patch_result.json"
)
SOURCE_TAG = "coin_path_patch_source"
VERIFY_TAG = "coin_path_patch_verify"


FUNCTION_FILES = {
    "ocv_lfp_base": "LFP_ocv.txt",
    "ocv_gr_discharge": "Gr_ocv.txt",
    "ely_sigma": "E_sigma.dat",
    "ely_D": "E_DL_int1.dat",
    "ely_tplus": "E_transpNm.dat",
}


def normalized(path):
    return str(Path(path).resolve()).casefold()


def main():
    if SOURCE.resolve() == OUTPUT_MODEL.resolve():
        raise ValueError("Output model must differ from source model")
    if OUTPUT_MODEL.exists():
        raise FileExistsError(OUTPUT_MODEL)

    expected = {}
    for tag, filename in FUNCTION_FILES.items():
        path = PARAM_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        expected[tag] = str(path.resolve())

    model = ModelUtil.load(SOURCE_TAG, str(SOURCE))
    try:
        before = {}
        for tag, path in expected.items():
            node = model.func().get(tag)
            before[tag] = str(node.getString("filename"))
            node.set("filename", path)
            node.importData()
        model.save(str(OUTPUT_MODEL))
    finally:
        ModelUtil.remove(SOURCE_TAG)

    verify_model = ModelUtil.load(VERIFY_TAG, str(OUTPUT_MODEL))
    try:
        after = {
            tag: str(verify_model.func().get(tag).getString("filename"))
            for tag in expected
        }
        assertions = {
            tag: normalized(after[tag]) == normalized(expected[tag])
            for tag in expected
        }
        if not all(assertions.values()):
            raise AssertionError(
                "Saved model path verification failed: "
                + json.dumps(assertions, ensure_ascii=False)
            )
        payload = {
            "ok": True,
            "source": str(SOURCE),
            "output_model": str(OUTPUT_MODEL),
            "source_unchanged": True,
            "before": before,
            "expected": expected,
            "after_reload": after,
            "assertions": assertions,
            "output_size_bytes": OUTPUT_MODEL.stat().st_size,
        }
    finally:
        ModelUtil.remove(VERIFY_TAG)

    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output_model": str(OUTPUT_MODEL)}, ensure_ascii=False))


main()
