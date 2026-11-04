"""Process entrypoint. Render injects PORT; the process binds all interfaces."""

import os

import uvicorn

from assetmind.api.app import create_app


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


app = create_app()
