import importlib.util
from pathlib import Path


LAUNCHER = Path(r"D:\Users\hez\Desktop\hithium\skills\comsol-battery-model-automation\scripts\run_mph_tool.py")
AUDIT_SCRIPT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260824_152850_cw501_loadcycle_diag2\solver_node_audit.py")

spec = importlib.util.spec_from_file_location("comsol_launcher", LAUNCHER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
client = module.SimClient()
lease = client.ensure_session()
try:
    print(client.exec_file(lease.session_id, AUDIT_SCRIPT))
finally:
    if lease.created:
        client.disconnect(lease.session_id)
