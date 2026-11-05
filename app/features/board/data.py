"""The board: one grid in memory, shared by every tab.

Nothing here knows about HTTP. Commands change a `Game`; views read one.
Everything runs on the app's one event loop, so no lock is needed.
"""

import math
import random
import time

COLORS = (
    "#ef4444",  # red
    "#f97316",  # orange
    "#eab308",  # yellow
    "#22c55e",  # green
    "#14b8a6",  # teal
    "#3b82f6",  # blue
    "#8b5cf6",  # violet
    "#ec4899",  # pink
    "#6366f1",  # indigo
    "#06b6d4",  # cyan
)
# A new round starts with this share of the cells painted, so it never looks empty.
FIRST_FILL = 0.3
# A full board celebrates this long; then the round starts again.
CELEBRATION_SECONDS = 4.0


class Game:
    def __init__(self, size: int = 5) -> None:
        self.size = size
        self.board: dict[int, str] = {}  # cell -> colour
        self.players: dict[str, str] = {}  # user_id -> colour, for each tab with an open stream
        self.celebrate_until = 0.0  # time.monotonic() when the celebration ends; 0 while playing
        self.new_round()

    @property
    def cells(self) -> int:
        return self.size * self.size

    @property
    def celebrating(self) -> bool:
        return self.celebrate_until > 0

    @property
    def seconds_left(self) -> int:
        """Whole seconds until the next round, rounded up; 0 while playing."""
        if not self.celebrating:
            return 0
        return max(0, math.ceil(self.celebrate_until - time.monotonic()))

    def new_round(self) -> None:
        cells = random.sample(range(self.cells), int(self.cells * FIRST_FILL))
        self.board = {cell: random.choice(COLORS) for cell in cells}
        self.celebrate_until = 0.0

    def join(self, user_id: str) -> None:
        # Seeded by the id, so a tab that reconnects keeps its colour.
        self.players.setdefault(user_id, random.Random(user_id).choice(COLORS))

    def leave(self, user_id: str) -> None:
        self.players.pop(user_id, None)

    def paint(self, user_id: str, cell: int) -> bool:
        """Paint the cell in the player's colour; the same colour again clears it.

        Returns False while the board celebrates: a full board is locked until the
        next round. The last cell painted starts the celebration.
        """
        if self.celebrating:
            return False
        color = self.players[user_id]
        if self.board.get(cell) == color:
            del self.board[cell]
        else:
            self.board[cell] = color
        if len(self.board) == self.cells:
            self.celebrate_until = time.monotonic() + CELEBRATION_SECONDS
        return True
