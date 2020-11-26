# The base cases: check all the boxes.
# This is fed by the hiher level piece.
from typing import List, Tuple, Iterable

from .box import Box

# The simplest check possible. Can return duplicates. Is very, very expensive.
# This is here for testing purposes: we know that it works, ergo we can test against it to make sure
# more complicated algorithms are right.
def check_exhaustive(boxes: List[Box]) -> Iterable[Tuple[Box, Box]]:
    for a in boxes:
        for b in boxes:
            # If the centers of the boxes are close enough together that they overlap in the x and y axis both, they overlap.
            # See the readme for the edge cases with box detection: in particular, it's not sufficient to check if one of the corners
            # is inside the other box.
            if (
                a is not b
                and abs(a.cx - b.cx) <= (a.half_width + b.half_width)
                and abs(a.cy - b.cy) <= (a.half_height + b.half_height)
            ):
                yield (a, b)


# This version does half the comparisons of check_exhaustive by using the fact that
# we know that we only need to check boxes to the right of what we've already done. Consider a list of 3 boxes [a, b, c].
# The first loop will check [(a, a), (a, b), (a, c)]
# This means that a has been checked against all the other boxes. The second loop then does:
# [(b, c)]
# And the third loop does nothing.
# Extend this to bigger cases, if you want further proof that it works.
#
# This variant also doesn't yield duplicated collision pairs, *and* we do this without having to check in a set.
def check_deduplicated(boxes: List[Box]) -> Iterable[Tuple[Box, Box]]:
    # Save the len function call.
    l = len(boxes)
    for i in range(l):
        # The inner loop only does l to the end of the boxes.
        for j in range(i + 1, l):
            a = boxes[i]
            b = boxes[j]
            if abs(a.cx - b.cx) <= (a.half_width + b.half_width) and abs(
                a.cy - b.cy
            ) <= (a.half_height + b.half_height):
                yield (a, b)
