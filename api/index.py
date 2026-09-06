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
    raw_app = create_app()

    class VercelWSGIWrapper:
        def __init__(self, wsgi_app):
            self.wsgi_app = wsgi_app

        def __call__(self, environ, start_response):
            path_info = environ.get("PATH_INFO", "")
            for prefix in ("/api/index.py", "/api/index"):
                if path_info == prefix:
                    environ["PATH_INFO"] = "/"
                    break
                elif path_info.startswith(prefix + "/"):
                    remainder = path_info[len(prefix):]
                    environ["PATH_INFO"] = remainder if remainder else "/"
                    break
            return self.wsgi_app(environ, start_response)

    app = VercelWSGIWrapper(raw_app)
    application = app
    handler = app
except Exception as e:
    err_msg = traceback.format_exc()
    print("Vercel Serverless Init Error:", err_msg, file=sys.stderr)
    from flask import Flask, jsonify
    fallback_app = Flask(__name__)
    app = fallback_app
    application = app
    handler = app

    @fallback_app.route("/", defaults={"path": ""})
    @fallback_app.route("/<path:path>")
    def catch_all(path):
        return jsonify({
            "error": "Serverless Initialization Error",
            "message": str(e),
            "traceback": err_msg
        }), 500

if __name__ == "__main__":
    from ui.app import create_app
    local_app = create_app()
    local_app.run(host="0.0.0.0", port=5050, debug=True)
