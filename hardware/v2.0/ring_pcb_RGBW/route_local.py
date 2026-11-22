"""Route remaining signals locally; KiCad is the final DRC oracle."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GEN = HERE / "generated"
jar = Path(sys.argv[1]).resolve(strict=True)
dsn, ses = GEN / "ring_pcb_RGBW.dsn", GEN / "ring_pcb_RGBW.ses"
with tempfile.TemporaryDirectory(prefix="lantern-rgbw-router-") as settings:
    command = ["java", "-jar", str(jar), "-de", str(dsn), "-do", str(ses),
               "-da", "--router.autorouter.max_passes=100",
               "--router.optimizer.max_threads=2", "--router.optimizer.enabled=false",
               "--router.fanout.enabled=false", "--router.autorouter.ignore_net_classes=Power",
               "--gui.enabled=false", "--api_server.enabled=false", "--mcp_server.enabled=false",
               "--router.automatic_neckdown=false", "--user_data_path=" + settings]
    with (GEN / "router.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    lines = (GEN / "router.log").read_text().splitlines()
    print("\n".join(lines[-25:]))
    result.check_returncode()
if not ses.is_file() or ses.stat().st_size == 0:
    raise RuntimeError("The local router did not export an SES")
manifest = {"engine": "Freerouting 2.5.0, local CLI; power fanout already placed/checked",
            "fixture": {"sha256": hashlib.sha256(dsn.read_bytes()).hexdigest()},
            "ses_sha256": hashlib.sha256(ses.read_bytes()).hexdigest(),
            "jar_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(),
            "final_state": "EXPORTED", "output_written": True,
            "scope": "SES exported; completeness and clearances must pass KiCad after import"}
(GEN / "router-result.json").write_text(json.dumps(manifest, indent=2) + "\n")
