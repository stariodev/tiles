# Tiles

One board that every visitor paints at once. A click in one tab shows in every other tab.

**Play:** [tiles.stario.dev](https://tiles.stario.dev) · **Build it step by step:** [the Realtime tiles tutorial](https://stario.dev/docs/tutorials/realtime-tiles)

Tiles is a small, complete [Stario](https://stario.dev) app. It is the app the tutorial builds in one file, laid out as a real project: one page, tests, and a deploy on [Yard](https://stario.dev/yard).

## How it works

The page is live: one response stays open and pushes HTML, and short commands change the state. Three routes do three jobs.

```text
GET  /       the page, once
GET  /live   stays open; sends the whole page again after each change
POST /click  paints one cell; answers 204, and the new board arrives on /live
```

1. `GET /` renders the board and gives the tab an id in a Datastar signal. On load, the page opens `GET /live`.
2. `GET /live` subscribes to an in-process `Relay`, sends the board, and waits. Each time anything publishes `board.changed`, it renders the page again and sends it. Datastar morphs only what differs.
3. `POST /click` reads the cell, validates it, answers an empty 204, paints the cell, and publishes `board.changed`. It never sends HTML. Every tab, including the one that clicked, gets the new board from its own stream.

A full board celebrates for four seconds, then a new round starts. A loop on a timer counts down and starts the round. It waits on `app.shutdown` between passes, so a deploy never waits for it.

## Read the code

Read it in this order. Each file has one job.

```text
app/
  main.py                    bootstrap: builds the Game and the Relay, registers the page, starts the round loop
  config.py                  every setting, read from the environment
  common/shell.py            the <html> document around every page
  common/framing.py          Framing: lets the sites in FRAME_ANCESTORS show the board in an iframe
  features/board/
    urls.py                  the three routes
    data.py                  the Game: the board and the players, with no HTTP in it
    views.py                 a Game in, HTML out
    handlers.py              TilesPage, one method per route, and the round loop
tests/test_board.py          the page loads, a click repaints two tabs, bad input gets 400
static/                      the stylesheet and Datastar
```

A few habits worth copying:

- **State lives on the server.** The browser holds one signal, the tab's `user_id`. Everything else is rendered from the `Game`.
- **One render for everything.** `render(user_id, game)` builds the first page and every patch. There is no second code path for updates.
- **A command never answers with HTML.** Read, validate, reply, then change the state and publish. Bad input gets `400` with a reason.
- **Subscribe before the first render**, so no change falls between them.
- **No module globals.** `bootstrap` builds the shared objects and hands them to the page class.

## Run it

You need [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
git clone https://github.com/stariodev/tiles
cd tiles
uv sync
uv run python -m app.main
```

Open http://127.0.0.1:8000 in two windows side by side and paint in one. With [just](https://just.systems), `just dev` reloads on every change, and `just check` formats, lints, type-checks, and runs the tests.

## Deploy it on Yard

On a host with [Yard](https://stario.dev/yard), one command deploys this repo and serves it over HTTPS:

```bash
yard app new --repo https://github.com/stariodev/tiles --caddy tiles.example.com
```

Yard sees a `pyproject.toml` that lists `stario` and a `uv.lock`, writes the container file, and starts `python -m app.main`. For your own copy, fork the repo and run `yard app new --caddy tiles.example.com` in your checkout. Each push then deploys.

| Setting | Default | What it does |
|---|---|---|
| `FRAME_ANCESTORS` | empty | Sites that may show the board in an iframe, separated by spaces, such as `https://stario.dev`. Empty means none. |

## Good to know

- **The board lives in memory.** A restart starts a new round, and that is fine for a game. For data that must survive a restart, see the [chat room tutorial](https://stario.dev/docs/tutorials/chat-room), which uses SQLite.
- **`Relay` is in-process.** One server process holds every tab. Several processes need a broker such as Redis in its place; the handlers keep their shape.
- **Sending the whole page on each change is deliberate.** It is simple, Datastar morphs only what differs, and the stream is compressed.

## Make it yours

Add a reset button: a `RESET = Route("POST /reset")`, a `reset` method on `TilesPage` that replies 204, calls `game.new_round()`, and publishes `board.changed`, and a button in `board_view` with `data.on("click", at.post(RESET.href()))`. The stream needs no change; it already repaints on every publish.

## License

MIT
