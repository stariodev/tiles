import json

from stario.testing import TestClient

from app.features.board.data import Game
from app.features.board.urls import CLICK, HOME, LIVE
from app.main import bootstrap


def tab(user_id: str) -> dict[str, str]:
    """A GET carries the tab's signals in the `datastar` query parameter."""
    return {"datastar": json.dumps({"user_id": user_id})}


async def test_home_loads(client):
    r = await client.get(HOME.href())
    assert r.status_code == 200
    assert 'id="board"' in r.text
    assert "/ 25 painted" in r.text


async def until(events, text: str, limit: int = 5) -> str:
    """The next event that holds `text`. A stream also repaints for joins, so skip those."""
    for _ in range(limit):
        event = await anext(events)
        if text in event["data"]:
            return event["data"]
    raise AssertionError(f"no event held {text!r}")


async def test_a_click_repaints_every_tab(client):
    async with (
        client.stream("GET", LIVE.href(), params=tab("t1"), timeout=2) as mine,
        client.stream("GET", LIVE.href(), params=tab("t2"), timeout=2) as other,
    ):
        one, two = mine.iter_events(), other.iter_events()
        await anext(one)  # the first paint of each tab
        await anext(two)
        # A cell that is not painted yet; t1 paints it, and both tabs show it.
        page = await client.get(HOME.href())
        cell = next(i for i in range(25) if f'data-cell="{i}" class="cell"' in page.text)
        r = await client.post(CLICK.href(query={"cell": str(cell)}), json={"user_id": "t1"})
        assert r.status_code == 204
        painted = f'data-cell="{cell}" class="cell painted"'
        assert painted in await until(one, painted)
        assert painted in await until(two, painted)


async def test_a_click_needs_an_open_stream(client):
    r = await client.post(CLICK.href(query={"cell": "0"}), json={"user_id": "nobody"})
    assert r.status_code == 400


async def test_bad_input_gets_400(client):
    async with client.stream("GET", LIVE.href(), params=tab("t1"), timeout=2) as live:
        await anext(live.iter_events())
        for cell in ("25", "-1", "x", ""):
            r = await client.post(CLICK.href(query={"cell": cell}), json={"user_id": "t1"})
            assert r.status_code == 400, cell
    r = await client.get(LIVE.href(), params=tab("not an id!"))
    assert r.status_code == 400


def test_the_last_cell_starts_the_celebration_and_locks_the_board():
    game = Game()
    game.join("t1")
    for cell in range(game.cells):
        if cell not in game.board:
            assert game.paint("t1", cell)
    assert game.celebrating
    assert 1 <= game.seconds_left <= 4
    assert not game.paint("t1", 0)  # locked until the next round
    game.new_round()
    assert not game.celebrating
    assert len(game.board) == int(game.cells * 0.3)


def test_the_same_colour_twice_clears_the_cell():
    game = Game()
    game.join("t1")
    game.board.clear()
    game.paint("t1", 3)
    assert 3 in game.board
    game.paint("t1", 3)
    assert 3 not in game.board


async def test_no_site_may_frame_the_board_by_default(client):
    r = await client.get(HOME.href())
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("content-security-policy") is None


async def test_frame_ancestors_lets_one_site_frame_it(monkeypatch):
    monkeypatch.setenv("FRAME_ANCESTORS", "https://stario.dev")
    async with TestClient(bootstrap, request_timeout=5) as client:
        r = await client.get(HOME.href())
    assert r.headers.get("x-frame-options") is None
    assert r.headers.get("content-security-policy") == "frame-ancestors 'self' https://stario.dev"


async def test_the_page_has_a_share_preview(client):
    r = await client.get(HOME.href())
    assert '<meta property="og:title" content="Tiles"/>' in r.text
    assert '<meta property="og:url" content="https://tiles.stario.dev"/>' in r.text
    assert (
        '<meta property="og:image" content="https://tiles.stario.dev/static/images/share.' in r.text
    )
    assert '<meta name="twitter:card" content="summary_large_image"/>' in r.text


async def test_public_url_sets_the_preview_links(monkeypatch):
    monkeypatch.setenv("PUBLIC_URL", "https://tiles.example.com/")
    async with TestClient(bootstrap, request_timeout=5) as client:
        r = await client.get(HOME.href())
    assert '<meta property="og:url" content="https://tiles.example.com"/>' in r.text
    assert (
        '<meta property="og:image" content="https://tiles.example.com/static/images/share.'
        in r.text
    )
