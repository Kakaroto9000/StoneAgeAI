"""Entry point: play Stone Age in the browser against the trained agent.

Usage:
    python play.py              # http://127.0.0.1:8000
    python play.py --port 9000 --host 0.0.0.0
    python play.py                              # AI uses your newest checkpoint (random if none)
    python play.py --model runs/2026-11-18_21-05-33/best.pth
    python play.py --model random               # AI plays random legal moves

--model is only the default: the browser's "Model" picker can choose any
checkpoint in models/ (or random moves) for each new game.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn  # noqa: E402

from stoneage_ai.checkpoints import latest_checkpoint  # noqa: E402
from stoneage_ai.paths import MODELS_DIR  # noqa: E402
from stoneage_ai.web import server  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Stone Age AI web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default="latest",
                        help="default checkpoint: 'latest' (newest saved checkpoint, the default), "
                             "a file in models/ (or a path), or 'random'")
    args = parser.parse_args()

    if args.model == "latest":
        server.configure(latest_checkpoint())
    elif args.model == "random":
        server.configure(None)
    else:
        path = Path(args.model)
        server.configure(path if path.exists() else MODELS_DIR / args.model)
    print(f"Stone Age AI running at http://{args.host}:{args.port}")
    uvicorn.run(server.app, host=args.host, port=args.port)
