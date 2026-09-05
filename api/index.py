import sys
import os
import traceback
from pathlib import Path

# Ensure workspace root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from ui.app import create_app
    app = create_app()
    application = app
except Exception as e:
    err_msg = traceback.format_exc()
    print("Vercel Serverless Init Error:", err_msg, file=sys.stderr)
    from flask import Flask, jsonify
    app = Flask(__name__)
    application = app

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

