# This partitions a list of boxes into subsets that might collide using a heuristic algorithm and some sorting.
from typing import List, Tuple, Iterable

from . import base_algorithms
from .box import Box

# Get an estimated center of a bunch of boxes.
def estimate_center(boxes: List[Box]) -> Tuple[float, float]:
    x = 0.0
    y = 0.0
    for b in boxes:
        x += b.cx
        y += b.cy
    return (x / len(boxes), y / len(boxes))


# Given a big list of boxes, partition it into 4 quadrants, where each quadrant contains all the boxes that overlap with
# the quadrant.  Boxes can be in more than 1 quadrant, if it's possible for them to collide with each other.
# Imagine this like an X where the center of the X is at the estimated center of all the boxes. If the box is in one corner of the X, then it can't collide
# with boxes in other corners.  But it's possible for a box to be on the line, in which case it might be in all of them.
def partition_quadrants(
    boxes: List[Box],
) -> Tuple[List[Box], List[Box], List[Box], List[Box]]:
    partition_bl = []
    partition_ul = []
    partition_br = []
    partition_ur = []
    center_x, center_y = estimate_center(boxes)
    for b in boxes:
        # If the minimum x of the box < center_x, it can be in either of the left quadrants.
        if b.x <= center_x:
            # If the minimum y < center_y, it's in the bottom left.
            if b.y <= center_y:
                partition_bl.append(b)
            # If the maximum y > center_y, it's also in the top left quadrant.
            if b.y2 >= center_y:
                partition_ul.append(b)
        # Same logic, but for the right half.
        if b.x2 >= center_x:
            if b.y <= center_y:
                partition_br.append(b)
            if b.y2 >= center_y:
                partition_ur.append(b)
    return (partition_bl, partition_ul, partition_br, partition_ur)


# This is a recursive function which partitions repeatedly until either
# a maximum number of iterations or a minimum partition size. In the best case, the function terminates early because the boxes are spread apart sparsely, but it's possible that partitioning won't ever break up a partition at all or will get stuck partitioning for a long time, if the boxes
# are all overlapping.
def partition(
    boxes: List[Box], partition_size: int, max_iterations: int, iteration: int = 0
) -> Iterable[List[Box]]:
    if iteration == max_iterations:
        # We got passed a partition, yield it up unchanged.
        yield boxes
        return
    for p in partition_quadrants(boxes):
        # Check the partition limit. Also, check if this partition shrunk at all. If it didn't shrink,
        # it probably can't be partitioned further, and we might as well not waste time on it.
        if len(p) <= partition_size or len(p) == len(boxes):
            yield p
            continue
        yield from partition(p, partition_size, max_iterations, iteration + 1)


# This isn't the final algorithm. For partitioning to really work for us, we also want some other stuff.
# See box_manager for what that other stuff is.
def check_partitioned(boxes: List[Box]) -> Iterable[Tuple[Box, Box]]:
    if len(boxes) == 0:
        return
    for p in partition(boxes, partition_size=10, max_iterations=2):
        yield from base_algorithms.check_deduplicated(p)
