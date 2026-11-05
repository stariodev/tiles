import asyncio
import uuid
from dataclasses import dataclass

from stario import App, Context, Relay, Writer
from stario.datastar import SSE, read_signals

from app.features.board.data import Game
from app.features.board.urls import CLICK, HOME, LIVE
from app.features.board.views import render

# Each change publishes {} on this subject. The payload carries nothing: every open
# stream reads the Game again and sends the whole page. Datastar morphs only what
# differs, and the writer compresses the stream, so a full page costs little.
CHANGED = "board.changed"


async def read_user_id(c: Context) -> str | None:
    """The tab's id from its signals, or None when it is missing or malformed."""
    user_id = str((await read_signals(c.req)).get("user_id", ""))
    return user_id if user_id.isalnum() and len(user_id) <= 32 else None


@dataclass(frozen=True, slots=True)
class TilesPage:
    """The board: one page, one stream, one command. Its fields are what it needs."""

    game: Game
    relay: Relay[dict]
    public_url: str  # for the share preview in the page head

    def register(self, app: App) -> None:
        app.add(HOME, self.home)
        app.add(LIVE, self.live)
        app.add(CLICK, self.click)

    async def home(self, c: Context, w: Writer) -> None:
        # A new id for each page load: two tabs are two players.
        w.html(render(uuid.uuid7().hex, self.game, self.public_url))

    async def live(self, c: Context, w: Writer) -> None:
        user_id = await read_user_id(c)
        if user_id is None:
            w.text("user_id must be a short id", status=400)
            return
        c.span.attr("user_id", user_id)

        # Subscribe before the first render, so no change falls between them.
        # latest=True keeps only the newest message, so a burst becomes one repaint.
        async with self.relay.subscribe(CHANGED, latest=True) as events:
            sse = SSE(w)
            self.game.join(user_id)
            self.relay.publish(CHANGED, {})  # the other tabs show the new player
            sse.patch_elements(render(user_id, self.game, self.public_url))
            # c.alive ends the loop when the tab closes or the server shuts down.
            async for _subject, _payload in c.alive(events):
                sse.patch_elements(render(user_id, self.game, self.public_url))

        self.game.leave(user_id)
        self.relay.publish(CHANGED, {})  # the other tabs drop this player

    async def click(self, c: Context, w: Writer) -> None:
        # 1. Read. 2. Validate.
        user_id = await read_user_id(c)
        cell = c.req.query.get("cell", "")
        if user_id is None or user_id not in self.game.players:
            w.text("open the board first: this tab has no stream", status=400)
            return
        if not cell.isdecimal() or int(cell) >= self.game.cells:
            w.text(f"cell must be a number from 0 to {self.game.cells - 1}", status=400)
            return
        c.span.attrs({"user_id": user_id, "cell": int(cell)})

        # 3. Reply: an empty 204. The new board is not in this response; it arrives
        # on every tab's stream, the clicking tab's too.
        w.empty()

        # 4. Execute, then tell every stream.
        if self.game.paint(user_id, int(cell)):
            self.relay.publish(CHANGED, {})


async def finish_rounds_forever(app: App, game: Game, relay: Relay[dict]) -> None:
    """While the board celebrates, repaint once a second for the countdown, then start a new round.

    A timer loop ends each pass by waiting on `app.shutdown`, never `asyncio.sleep`:
    the wait returns at once when the server drains.
    """
    shutdown = app.shutdown  # read once; each read is a new shield
    shown = -1
    while not app.shutting_down:
        if game.celebrating:
            left = game.seconds_left
            if left == 0:
                game.new_round()
                shown = -1
                relay.publish(CHANGED, {})
            elif left != shown:
                shown = left
                relay.publish(CHANGED, {})
        await asyncio.wait({shutdown}, timeout=0.25)
