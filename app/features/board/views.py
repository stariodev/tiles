"""Views: a Game in, HTML out.

The same `render` builds the first page and every patch on the stream, so the page
always shows what the server knows. A view never changes state and never fetches.
"""

from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement, classes, styles

from app.common.shell import page
from app.features.board.data import Game
from app.features.board.urls import CLICK, LIVE

# Seconds between two cells lighting up in the celebration wave.
WAVE_STEP = 0.04
SPARKLES = 14


def render(user_id: str, game: Game) -> HtmlElement:
    return page(
        "Tiles",
        h.Main(
            # The patch target. Its id, signals, and data-init stay the same in every render.
            {"id": "home", "class": "container"},
            # The tab's id. Datastar sends it with every request; if_missing keeps it
            # when a patch arrives.
            data.signals({"user_id": user_id}, if_missing=True),
            # Opens GET /live when the page loads, and reopens it after a network blip.
            data.init(at.get(LIVE.href(), retry="always")),
            info_view(user_id, game),
            board_view(game),
        ),
    )


def swatch(color: str) -> HtmlElement:
    return h.Span({"class": "swatch"}, styles({"background-color": color}))


def info_view(user_id: str, game: Game) -> HtmlElement:
    if game.celebrating:
        left = game.seconds_left
        status = h.Div(
            {"class": "info-row"},
            h.Span({"class": "info-label info-label--complete"}, "Full board"),
            h.Span(
                {"class": "info-stats info-stats--complete"},
                f"New round in {left}…" if left else "Starting…",
            ),
        )
    else:
        status = h.Div(
            {"class": "info-row"},
            h.Span({"class": "info-label"}, "Progress"),
            h.Span(
                {"class": "info-stats"},
                h.Span({"class": "count"}, str(len(game.board))),
                f" / {game.cells} painted",
            ),
        )
    return h.Div(
        {"id": "info", "class": "info-panel"},
        status,
        h.Div(
            {"class": "info-row"},
            h.Span({"class": "info-label"}, "Players"),
            h.Ul(
                {"class": "users-list"},
                [h.Li(swatch(color)) for color in game.players.values()]
                or [h.Li({"class": "empty"}, "…")],
            ),
        ),
        h.Div(
            {"class": "info-row"},
            h.Span({"class": "info-label"}, "Your color"),
            # Before the stream opens, this tab has no colour yet.
            swatch(game.players.get(user_id, "#ccc")),
        ),
    )


def cell_view(cell: int, game: Game) -> HtmlElement:
    color = game.board.get(cell)
    style: dict[str, str] = {}
    if color:
        style["background-color"] = color
    if game.celebrating:
        style["animation-delay"] = f"{cell * WAVE_STEP:.2f}s"
    return h.Div(
        {"data-cell": str(cell)},
        classes("cell", "painted" if color else None),
        styles(style) if style else None,
    )


def board_view(game: Game) -> HtmlElement:
    full = len(game.board) == game.cells
    return h.Div(
        {"class": "board-wrap"},
        h.Div(
            {"id": "board"},
            classes(
                "board", "complete" if full else None, "celebrating" if game.celebrating else None
            ),
            # One listener for the whole board. A click on a cell posts its number;
            # a click on a gap between cells has no data-cell and posts nothing.
            data.on(
                "click",
                f"evt.target.dataset.cell && @post(`{CLICK.href()}?cell=${{evt.target.dataset.cell}}`)",
            ),
            [
                h.Div(
                    {"class": "row"},
                    [cell_view(row * game.size + col, game) for col in range(game.size)],
                )
                for row in range(game.size)
            ],
            sparkles_view() if game.celebrating else None,
        ),
    )


def sparkles_view() -> HtmlElement:
    # Fixed positions spread over the board; the stylesheet animates them.
    return h.Div(
        {"class": "board-sparkles"},
        [
            h.Span(
                {"class": "sparkle"},
                styles(
                    {
                        "left": f"{(i * 17 + 11) % 84 + 8}%",
                        "top": f"{(i * 23 + 7) % 84 + 8}%",
                        "animation-delay": f"{i * 0.12:.2f}s",
                    }
                ),
            )
            for i in range(SPARKLES)
        ],
    )
