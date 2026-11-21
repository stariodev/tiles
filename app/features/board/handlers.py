import asyncio
import uuid
from dataclasses import dataclass

from stario import App, Context, Relay, Writer
from stario.datastar import SSE, read_signals

from app.features.board.data import DEFAULT_SIZE, SIZES, Game
from app.features.board.urls import CLICK, HOME, LIVE
from app.features.board.views import render

# Each change publishes {} on this subject plus the board size, so a click on the
# 8x8 board repaints only the 8x8 streams. The payload carries nothing: every open
# stream reads its Game again and sends the whole page. Datastar morphs only what
# differs, and the writer compresses the stream, so a full page costs little.
CHANGED = "board.changed"
# A tab joined or left some board. Every stream repaints, since every page shows
# how many play on each size.
PLAYERS = "board.players"


async def read_user_id(c: Context) -> str | None:
    """The tab's id from its signals, or None when it is missing or malformed."""
    user_id = str((await read_signals(c.req)).get("user_id", ""))
    return user_id if user_id.isalnum() and len(user_id) <= 32 else None


def changed(game: Game) -> str:
    """The subject that the streams of this board follow."""
    return f"{CHANGED}.{game.size}"


@dataclass(frozen=True, slots=True)
class TilesPage:
    """The board: one page, one stream, one command. Its fields are what it needs."""

    games: dict[int, Game]  # one shared board per size in SIZES
    relay: Relay[dict]
    public_url: str  # for the share preview in the page head

    def register(self, app: App) -> None:
        app.add(HOME, self.home)
        app.add(LIVE, self.live)
        app.add(CLICK, self.click)

    def game_for(self, c: Context) -> Game | None:
        """The board that `?size=` names: the default board without one, None for an unknown size."""
        size = c.req.query.get("size", str(DEFAULT_SIZE))
        return self.games.get(int(size)) if size.isdecimal() else None

    async def home(self, c: Context, w: Writer) -> None:
        game = self.game_for(c)
        if game is None:
            w.text(f"size must be one of {', '.join(map(str, SIZES))}", status=404)
            return
        # A new id for each page load: two tabs are two players.
        w.html(render(uuid.uuid7().hex, game, self.games, self.public_url))

    async def live(self, c: Context, w: Writer) -> None:
        user_id = await read_user_id(c)
        game = self.game_for(c)
        if user_id is None or game is None:
            w.text("user_id must be a short id and size a board size", status=400)
            return
        c.span.attrs({"user_id": user_id, "size": game.size})

        # Subscribe before the first render, so no change falls between them.
        # latest=True keeps only the newest message, so a burst becomes one repaint.
        async with self.relay.subscribe(changed(game), PLAYERS, latest=True) as events:
            sse = SSE(w)
            game.join(user_id)
            self.relay.publish(PLAYERS, {})  # every tab shows the new player
            sse.patch_elements(render(user_id, game, self.games, self.public_url))
            # c.alive ends the loop when the tab closes or the server shuts down.
            async for _subject, _payload in c.alive(events):
                sse.patch_elements(render(user_id, game, self.games, self.public_url))

        game.leave(user_id)
        self.relay.publish(PLAYERS, {})  # every tab drops this player

    async def click(self, c: Context, w: Writer) -> None:
        # 1. Read. 2. Validate.
        user_id = await read_user_id(c)
        game = self.game_for(c)
        cell = c.req.query.get("cell", "")
        if game is None:
            w.text(f"size must be one of {', '.join(map(str, SIZES))}", status=400)
            return
        if user_id is None or user_id not in game.players:
            w.text("open the board first: this tab has no stream", status=400)
            return
        if not cell.isdecimal() or int(cell) >= game.cells:
            w.text(f"cell must be a number from 0 to {game.cells - 1}", status=400)
            return
        c.span.attrs({"user_id": user_id, "size": game.size, "cell": int(cell)})

        # 3. Reply: an empty 204. The new board is not in this response; it arrives
        # on every tab's stream, the clicking tab's too.
        w.empty()

        # 4. Execute, then tell every stream.
        if game.paint(user_id, int(cell)):
            self.relay.publish(changed(game), {})


async def finish_rounds_forever(app: App, games: dict[int, Game], relay: Relay[dict]) -> None:
    """While a board celebrates, repaint it once a second for the countdown, then start a new round.

    A timer loop ends each pass by waiting on `app.shutdown`, never `asyncio.sleep`:
    the wait returns at once when the server drains.
    """
    shutdown = app.shutdown  # read once; each read is a new shield
    shown = dict.fromkeys(games, -1)  # size -> the countdown its streams last showed
    while not app.shutting_down:
        for size, game in games.items():
            if not game.celebrating:
                continue
            left = game.seconds_left
            if left == 0:
                game.new_round()
                shown[size] = -1
                relay.publish(changed(game), {})
            elif left != shown[size]:
                shown[size] = left
                relay.publish(changed(game), {})
        await asyncio.wait({shutdown}, timeout=0.25)
