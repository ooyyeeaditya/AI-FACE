import os
import sys
import traceback
from pathlib import Path

_CURRENT_DIR = Path(__file__).resolve().parent
_ROOT = _CURRENT_DIR.parent

for _p in [str(_ROOT), str(_CURRENT_DIR), os.getcwd()]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from ui.app import create_app
    app = create_app()
    application = app
    handler = app
except Exception as e:
    err_msg = traceback.format_exc()
    print("Vercel Serverless Init Error:", err_msg, file=sys.stderr)
    from flask import Flask, jsonify
    app = Flask(__name__)
    application = app
    handler = app

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        return jsonify({
            "error": "Serverless Initialization Error",
            "message": str(e),
            "traceback": err_msg
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)


