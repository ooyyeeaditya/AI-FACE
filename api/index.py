import sys
from pathlib import Path

# Ensure workspace root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ui.app import create_app

# Vercel serverless application entrypoint
app = create_app()
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
