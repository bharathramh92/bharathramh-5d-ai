import os
import sys
import uvicorn

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ["--host", "--port"]:
        from src.cli import main as cli_main
        cli_main()
    else:
        port = int(os.getenv("PORT", 8000))
        print(f"⚡ Starting ArchAgent Server on http://localhost:{port} ...")
        uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=False)
