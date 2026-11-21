from stario import Route

# Three routes, three jobs. Each takes `?size=` to pick the board; no size is the
# default board, so the plain URLs keep working:
HOME = Route("GET /")  # the page, once
LIVE = Route("GET /live")  # stays open and sends the board again after each change
CLICK = Route("POST /click")  # paints one cell; answers 204, the board arrives on LIVE
