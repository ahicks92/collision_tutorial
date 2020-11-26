from typing import Any


class Box:
    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        userdata: Any = None,
        stationary: bool = False,
    ) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.stationary = stationary
        # Used for optimization of collision detection.
        self.half_width = width / 2
        self.half_height = height / 2
        self._after_move()
        # Stash the userdata so that users can link this back to something
        self.userdata = userdata
        self.manager = None

    def _after_move(self):
        # Update x2 and y2, so that we have both views on the data.
        self.x2 = self.x + self.width
        self.y2 = self.y + self.height
        # Maintain the center of the box as well.
        self.cx = self.x + self.half_width
        self.cy = self.y + self.half_height

    def move(self, new_x: float, new_y: float) -> None:
        self.x = new_x
        self.y = new_y
        self._after_move()
        if self.manager and self.stationary:
            self.manager.invalidate_stationary_cache()

    def __repr__(self):
        return f"Box(x={self.x}, y={self.y}, width={self.width}, height={self.height}, stationary={self.stationary})"
