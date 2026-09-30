from __future__ import annotations

from mangum import Mangum

from knock_knock.api.main import app

handler = Mangum(app, lifespan="auto")
