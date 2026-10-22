"""Start the local dashboard with python -m dashboard."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("dashboard.app:app", host="127.0.0.1", port=8765)
