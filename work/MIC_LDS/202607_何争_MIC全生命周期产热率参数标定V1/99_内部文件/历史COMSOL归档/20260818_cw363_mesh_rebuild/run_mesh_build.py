import json
import sys
from pathlib import Path


SKILL_SCRIPTS = Path(r"C:\HithiumSSD\hithium\skills\comsol-battery-model-automation\scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))

from run_mph_tool import SimClient


SCRIPT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260818_cw363_mesh_rebuild\build_mesh.py")
MANIFEST = SCRIPT.with_name("build_mesh.session.json")

client = SimClient()
lease = client.ensure_session()
try:
    response = client.exec_file(lease.session_id, SCRIPT)
    MANIFEST.write_text(
        json.dumps(
            {
                "session_id": lease.session_id,
                "created_by_launcher": lease.created,
                "action": "mesh_build_save_reload_verify",
                "script": str(SCRIPT),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(response, ensure_ascii=False))
finally:
    if lease.created:
        client.disconnect(lease.session_id)
