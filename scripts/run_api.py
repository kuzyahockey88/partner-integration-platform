import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    uvicorn.run(
        "services.api.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )