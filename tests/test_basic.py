from hypothesis import given, settings

from collision_tutorial import (
    box,
    base_algorithms,
    test_helpers,
    partitioner,
    box_manager,
)
from .hypothesis_helpers import *


@given(boxes=BOXES_ST)
@settings(max_examples=2000)
def test_base_algorithms_equivalence(boxes):
    # Test that both base algorithms will output the same thing after deduplication is applied.
    # We do so by duplicating the second one by inserting all the pairs, then we see if the sets are equivalent with intersection.
    collisions_a = list(base_algorithms.check_exhaustive(boxes))
    collisions_b = list(base_algorithms.check_deduplicated(boxes))
    set_a = set(collisions_a)
    set_b = set()
    for a, b in collisions_b:
        set_b.add((a, b))
        set_b.add((b, a))
    assert len(set_a.intersection(set_b)) == len(collisions_a)
    assert len(collisions_a) == 2 * len(collisions_b)


@given(boxes=BOXES_ST)
@settings(max_examples=2000)
def test_partitioner(boxes):
    good = base_algorithms.check_deduplicated(boxes)
    p = partitioner.check_partitioned(boxes)
    good_s = set(good)
    p_s = set(p)
    assert len(good_s.intersection(p_s)) == len(good_s)


# A very basic fuzz test. See test_manager.py for the RulebasedStateMachine version,
# which also checks things like whether or not moving stationary boxes causes problems.
@given(boxes=BOXES_ST)
@settings(max_examples=2000)
def test_manager_basic(boxes):
    good = base_algorithms.check_deduplicated(boxes)
    good_s = set(good)
    manager = box_manager.BoxManager()
    for b in boxes:
        manager.register(b)
    got = manager.yield_collisions()
    got_s = set(got)
    assert len(good_s.intersection(got_s)) == len(good_s)
