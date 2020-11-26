# We can get evenmore speed from holding some state as to whether or not we expect boxes to move and,
# if not, caching some of the collision steps.
#
# Doing this requires going via a manager class that can track movement.
import math
from typing import Tuple, Iterable, List

from .box import Box
from . import partitioner


class BoxManager:
    def __init__(self):
        self.boxes = []
        self.stationary_cache = []
        self.stationary_cache_valid = True
        self.stationary_count = 0

    def register(self, box: Box) -> None:
        self.boxes.append(box)
        # inject ourselves as the manager.
        box.manager = self
        if box.stationary:
            self.stationary_cache_valid = False
            self.stationary_count += 1

    def remove(self, box: Box) -> None:
        self.boxes.remove(box)
        box.manager = None
        if box.stationary:
            self.invalidate_stationary_cache()
            self.stationary_count -= 1

    def invalidate_stationary_cache(self) -> None:
        self.stationary_cache_valid = False

    def yield_collisions(self) -> Iterable[Tuple[Box, Box]]:
        # No stationary boxes means we shouldn't even bother optimizing.
        if self.stationary_count == 0:
            yield from partitioner.check_partitioned(self.boxes)
        elif not self.stationary_cache_valid:
            self.stationary_cache = []
            for a, b in self._do_not_optimized():
                if a.stationary and b.stationary:
                    self.stationary_cache.append((a, b))
                yield (a, b)
                self.stationary_cache_valid = True
        else:
            yield from self.stationary_cache
            # If all the boxes are stationary, all the collisions are always already cached.
            if len(self.boxes) == self.stationary_count:
                return
            yield from self._do_optimized()

    def _do_not_optimized(self) -> Iterable[Tuple[Box, Box]]:
        # Just ask the partitioner nicely.
        return partitioner.check_partitioned(self.boxes)

    def _do_optimized(self) -> Iterable[Tuple[Box, Box]]:
        # See below.
        return check_partition_optimized(self.boxes, self.stationary_count)


# An optimized checker that assumes that all stationary to stationary collisions are cached. Additionally, it inlines all the functions so that we don't pay the Python function overhead.
def check_partition_optimized(boxes: List[Box], stationary_count: int):
    if len(boxes) == 0:
        return
    # We want roughly equal numbers of stationary boxes in each partition, and
    # we can assume that they're free (see below).
    # stationary/len(boxes) is the probability of a single box being stationary, and the partitioner's worst case is sampling with replacement.
    # We have:
    # nonstationary  = size * (1 - stationary_percent)
    # nonstationary / (1 - stationary_percent) = size
    partition_size = max(10, math.ceil(10 / (1 - stationary_count / len(boxes))))
    for part in partitioner.partition(boxes, partition_size, 2):
        # The trick of optimizing stationary boxes is realizing that if we put all the stationary boxes at the end,
        # we can use the same trick as in check_deduplicated. Only, this time, we stop the outer loop when it hits a stationary box:
        # at that point, we know that we'll just yield already-cached stationary pairs.
        part.sort(key=lambda b: b.stationary)
        l = len(part)
        for i in range(l):
            if part[i].stationary:
                break
            for j in range(i + 1, l):
                a = part[i]
                b = part[j]
                if abs(a.cx - b.cx) <= (a.half_width + b.half_width) and abs(
                    a.cy - b.cy
                ) <= (a.half_height + b.half_height):
                    yield (a, b)
