import importlib.util
import sys
from pathlib import Path


LAUNCHER = Path(r"C:\HithiumSSD\hithium\skills\comsol-battery-model-automation\scripts\run_mph_tool.py")


def main():
    script = Path(sys.argv[1]).resolve()
    spec = importlib.util.spec_from_file_location("comsol_launcher", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = module.SimClient()
    lease = client.ensure_session()
    try:
        print(client.exec_file(lease.session_id, script))
    finally:
        if lease.created:
            client.disconnect(lease.session_id)


if __name__ == "__main__":
    main()
