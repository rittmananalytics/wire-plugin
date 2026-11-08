#!/usr/bin/env python3
"""The Wire CLI (experimental, wire#408 item 2).

    python3 wire/cli/wire.py <command> <release> [args]    typed run of one Wire command
    python3 wire/cli/wire.py run <release>                 orchestrate: runnable set, lanes, record
    python3 wire/cli/wire.py status <release>              states, runnable set, claim, next action
    python3 wire/cli/wire.py gate <release> <command>      the precondition gate's answer
    python3 wire/cli/wire.py exec "<prompt>"               headless run through the harness
    python3 wire/cli/wire.py codex-install [<repo>]        the Codex plugin's install set

See wire/cli/README.md. Standard library plus PyYAML (which Studio's resolver,
the executable form of specs/utils/runnable_set.md, already needs).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wire_cli.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
