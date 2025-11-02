import uvicorn

from app.core.app import create_app
from app.core.config import get_settings

app = create_app()


def run() -> None:
    """Entrypoint for `mindwell-api` script."""
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        factory=False,
    )


if __name__ == "__main__":
    run()
