import sys
import os
from pathlib import Path
import uvicorn

# Ensure backend directory is in python sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting Multi-Agent Software Team Server on http://127.0.0.1:{port}")
    app_dir = backend_dir / "app"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[str(app_dir)],
    )
