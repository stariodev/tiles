from stario import h
from stario.datastar import ModuleScript, data
from stario.markup import HtmlElement, baked

from app.assets import DATASTAR_JS, SCRIPTS, STYLE_CSS

DESCRIPTION = (
    "One board that every visitor paints at once. A click in one tab shows in every other tab."
)


@baked
def page(title: str, body: HtmlElement, url: str, image: str) -> HtmlElement:
    """The document. `url` and `image` are absolute: the page's address and its share picture."""
    return h.HtmlDocument(
        {"lang": "en"},
        h.Head(
            h.Meta({"charset": "utf-8"}),
            h.Meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
            h.Title(title),
            h.Meta({"name": "description", "content": DESCRIPTION}),
            # Open Graph and Twitter tags: the title, text, and picture of a shared link.
            h.Meta({"property": "og:type", "content": "website"}),
            h.Meta({"property": "og:site_name", "content": "Stario"}),
            h.Meta({"property": "og:title", "content": title}),
            h.Meta({"property": "og:description", "content": DESCRIPTION}),
            h.Meta({"property": "og:url", "content": url}),
            h.Meta({"property": "og:image", "content": image}),
            h.Meta({"property": "og:image:width", "content": "960"}),
            h.Meta({"property": "og:image:height", "content": "600"}),
            h.Meta({"name": "twitter:card", "content": "summary_large_image"}),
            h.Link({"rel": "stylesheet", "href": STYLE_CSS}),
            *[h.Script({"src": src, "defer": True}) for src in SCRIPTS],
            ModuleScript(DATASTAR_JS),
        ),
        h.Body(
            body,
            h.Output(
                {"id": "toast", "role": "status"},
                data.signals({"_toast": ""}, if_missing=True),
                data.show("$_toast"),
                data.text("$_toast"),
                data.effect("$_toast && setTimeout(() => $_toast = '', 4000)"),
            ),
        ),
    )
