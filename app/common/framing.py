from dataclasses import dataclass

from stario import Context, Handler, Writer


@dataclass(frozen=True, slots=True)
class Framing:
    """Lets the origins in `ancestors` (space-separated) show the pages in an <iframe>, and no others.

    `security_headers()` sends `x-frame-options: DENY`, which allows no site at all and
    cannot name one. This Content-Security-Policy names them. It sets nothing else, so
    Datastar expressions still run. `bootstrap` builds one and uses `framing.attach`.
    """

    ancestors: str

    def attach(self, inner: Handler) -> Handler:
        policy = f"frame-ancestors 'self' {self.ancestors}"

        async def handler(c: Context, w: Writer) -> None:
            w.headers.set("content-security-policy", policy)
            await inner(c, w)

        return handler
