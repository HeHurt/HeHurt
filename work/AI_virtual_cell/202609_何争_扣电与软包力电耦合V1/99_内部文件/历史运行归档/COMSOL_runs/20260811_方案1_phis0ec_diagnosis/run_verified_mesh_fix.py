import json
import sys
from pathlib import Path

skill_scripts = Path(r"C:\HithiumSSD\hithium\skills\comsol-java-battery-modeling\scripts")
sys.path.insert(0, str(skill_scripts))
from run_mph_tool import SimClient

script = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\apply_verified_mesh_fix.py")
manifest = script.with_name("apply_verified_mesh_fix.session.json")
client = SimClient()
lease = client.ensure_session()
try:
    response = client.exec_file(lease.session_id, script)
    manifest.write_text(
        json.dumps(
            {
                "session_id": lease.session_id,
                "created_by_launcher": lease.created,
                "action": "patch_reload_smoke",
                "script": str(script),
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
