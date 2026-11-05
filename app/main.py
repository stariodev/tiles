import asyncio

from stario import App, Relay, Span, serve
from stario.http import same_origin, security_headers

from app.assets import ASSETS
from app.common.framing import Framing
from app.config import Config
from app.features.board.data import Game
from app.features.board.handlers import TilesPage, finish_rounds_forever


async def bootstrap(app: App, span: Span):
    """Build the shared objects, register the page, and run until shutdown.

    Everything the app shares lives here and is handed to the page. No module globals.
    """
    config = Config.from_env()
    # same_origin: a POST from another site gets 403. security_headers: nosniff, a
    # referrer policy, and no framing, unless FRAME_ANCESTORS names who may frame it.
    if config.frame_ancestors:
        framing = Framing(config.frame_ancestors)
        app.use("/", same_origin(), security_headers(frame=None), framing.attach)
    else:
        app.use("/", same_origin(), security_headers())
    span.attrs(await ASSETS.attach(app))

    game = Game()
    relay: Relay[dict] = Relay()  # in-process fan-out between the open streams
    span.attrs({"tiles.cells": game.cells, "tiles.frame_ancestors": config.frame_ancestors})

    # pages
    TilesPage(game, relay).register(app)

    app.create_task(finish_rounds_forever(app, game, relay), name="tiles.rounds")
    yield


if __name__ == "__main__":
    asyncio.run(serve(bootstrap))
