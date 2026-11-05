from stario import Context, Handler, Writer
from stario.http.middleware import Middleware


def allow_framing(origins: str) -> Middleware:
    """Let these origins (space-separated) show the pages in an <iframe>, and no others.

    `security_headers()` sends `x-frame-options: DENY`, which allows no site at all and
    cannot name one. This Content-Security-Policy names them. It sets nothing else, so
    Datastar expressions still run.
    """
    policy = f"frame-ancestors 'self' {origins}"

    def middleware(inner: Handler) -> Handler:
        async def handler(c: Context, w: Writer) -> None:
            w.headers.set("content-security-policy", policy)
            await inner(c, w)

        return handler

    return middleware
