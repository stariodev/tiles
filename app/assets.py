from pathlib import Path

from stario import Assets

ASSETS = Assets(Path(__file__).resolve().parents[1] / "static", url_prefix="/static")
STYLE_CSS = ASSETS.href("css/style.css")
DATASTAR_JS = ASSETS.href("js/datastar.js")
# The picture a chat or a social site shows for a shared link: 960x600, from the demo clip.
SHARE_IMAGE = ASSETS.href("images/share.jpg")
# Client behaviour lives in static/js/<name>.js — each file defines app.<name>.
SCRIPTS: tuple[str, ...] = ()
