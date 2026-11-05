from stario import Route

# Three routes, three jobs:
HOME = Route("GET /")  # the page, once
LIVE = Route("GET /live")  # stays open and sends the board again after each change
CLICK = Route("POST /click")  # paints one cell; answers 204, the board arrives on LIVE
