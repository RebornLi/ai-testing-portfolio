# Root conftest.py
#
# Make every lab importable under ANY pytest --import-mode.
#
# Each lab exposes its sources as a top-level package imported from the lab
# *root* directory:
#
#     agent-lab/  -> from agentlab.agent        (needs agent-lab/  on sys.path)
#     eval-lab/   -> from evalagents.agent      (needs eval-lab/  on sys.path)
#     auto-eval/  -> from autoeval.agent        (needs auto-eval/ on sys.path)
#     security-lab/ -> from security / from vault
#     rag-demo/   -> from pipeline / report / ...
#
# pytest's default "prepend" mode auto-inserts each test file's own directory
# onto sys.path, which accidentally exposes agent-lab/ and eval-lab/ — that's
# why those labs pass under prepend. `importlib` mode does NOT do that
# insertion, so we add the package-parent dirs explicitly here. This keeps
# per-lab and combined runs green under both import modes.
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# Order matters only for readability; we dedupe below.
LAB_ROOTS = ("agent-lab", "eval-lab", "auto-eval", "security-lab", "rag-demo")

for _lab in LAB_ROOTS:
    _path = os.path.join(ROOT, _lab)
    if _path not in sys.path:
        sys.path.insert(0, _path)
