import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"⚡ Starting ArchAgent Server on http://localhost:{port} ...")
    uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=True)
