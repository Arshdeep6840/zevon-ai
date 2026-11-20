"""Main application entrypoint alias for uvicorn app.main:app."""

from services.api.main import app, start

__all__ = ["app", "start"]

if __name__ == "__main__":
    start()
