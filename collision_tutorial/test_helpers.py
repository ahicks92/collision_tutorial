import random
from typing import List

from .box import Box


def generate_random_boxes(
    n: int,
    seed: int,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    min_width: float,
    max_width: float,
    min_height: float,
    max_height: float,
    stationary_probability: float = 0.0,
) -> List[Box]:
    rng = random.Random(seed)
    d_x = max_x - min_x
    d_y = max_y - min_y
    d_width = max_width - min_width
    d_height = max_height - min_height
    boxes = []
    for i in range(n):
        x = rng.random() * d_x + min_x
        y = rng.random() * d_y + min_y
        width = rng.random() * d_width + min_width
        height = rng.random() * d_height + min_height
        boxes.append(
            Box(
                x=x,
                y=y,
                width=width,
                height=height,
                stationary=rng.random() < stationary_probability,
            )
        )
    return boxes
