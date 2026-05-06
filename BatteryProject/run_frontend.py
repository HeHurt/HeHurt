from __future__ import annotations

import argparse
import importlib.metadata
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "output"
STDOUT_LOG = LOG_DIR / "streamlit_frontend.log"
STDERR_LOG = LOG_DIR / "streamlit_frontend.err.log"
RUNTIME_ROOT = Path(tempfile.gettempdir()) / "batteryproject_streamlit"
RUNTIME_HOME = RUNTIME_ROOT / "home"
MPL_CONFIG_DIR = RUNTIME_ROOT / f"mpl_{os.getpid()}"
LOG_DIR.mkdir(exist_ok=True)
RUNTIME_ROOT.mkdir(exist_ok=True)
RUNTIME_HOME.mkdir(exist_ok=True)
MPL_CONFIG_DIR.mkdir(exist_ok=True)

os.environ.setdefault("PYBAMM_DISABLE_TELEMETRY", "true")
os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
os.environ.setdefault("HOME", str(RUNTIME_HOME))
os.environ.setdefault("USERPROFILE", str(RUNTIME_HOME))
os.environ.setdefault("APPDATA", str(RUNTIME_HOME / "AppData" / "Roaming"))
os.environ.setdefault("LOCALAPPDATA", str(RUNTIME_HOME / "AppData" / "Local"))
os.environ.setdefault("HOMEDRIVE", RUNTIME_HOME.drive)
os.environ.setdefault("HOMEPATH", "\\" + "\\".join(RUNTIME_HOME.parts[1:]) if len(RUNTIME_HOME.parts) > 1 else "\\")
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))
(RUNTIME_HOME / "AppData" / "Roaming").mkdir(parents=True, exist_ok=True)
(RUNTIME_HOME / "AppData" / "Local").mkdir(parents=True, exist_ok=True)


def redirect_process_output() -> None:
    sys.stdout = open(STDOUT_LOG, "a", encoding="utf-8", buffering=1)
    sys.stderr = open(STDERR_LOG, "a", encoding="utf-8", buffering=1)
    print("")
    print("=== BatteryProject frontend launcher ===")


def patch_streamlit_version() -> str:
    try:
        version_value = importlib.metadata.version("streamlit")
    except Exception:
        version_value = None
    if not version_value:
        version_value = "local-build"

    import streamlit
    import streamlit.runtime.app_session as app_session
    import streamlit.runtime.metrics_util as metrics_util
    import streamlit.version as streamlit_version

    streamlit.__version__ = version_value
    streamlit_version.STREAMLIT_VERSION_STRING = version_value
    app_session.STREAMLIT_VERSION_STRING = version_value
    metrics_util._get_machine_id_v4 = lambda: "local-machine-id-v4"
    metrics_util.Installation._instance = None

    def _patched_populate_user_info_msg(msg) -> None:
        msg.installation_id = "local-installation-id"
        msg.installation_id_v3 = "local-installation-id-v3"
        msg.installation_id_v4 = "local-installation-id-v4"

    app_session._populate_user_info_msg = _patched_populate_user_info_msg
    return version_value


def main() -> None:
    redirect_process_output()
    parser = argparse.ArgumentParser(description="Launch BatteryProject Streamlit frontend")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit server port")
    parser.add_argument("--address", default="localhost", help="Bind address")
    args = parser.parse_args()

    version_value = patch_streamlit_version()
    print(f"Runtime home: {RUNTIME_HOME}")
    print(f"Matplotlib config dir: {MPL_CONFIG_DIR}")
    print(f"Patched Streamlit version: {version_value}")

    from streamlit.web import bootstrap

    bootstrap.run(
        str(PROJECT_ROOT / "frontend.py"),
        False,
        [],
        {
            "server.headless": True,
            "server.port": args.port,
            "server.address": args.address,
            "browser.gatherUsageStats": False,
        },
    )


if __name__ == "__main__":
    main()
