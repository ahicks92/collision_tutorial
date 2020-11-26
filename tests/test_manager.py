import hypothesis.strategies as st
from hypothesis.stateful import (
    Bundle,
    consumes,
    RuleBasedStateMachine,
    rule,
    multiple,
    invariant,
)

from collision_tutorial import box, box_manager, base_algorithms
from .hypothesis_helpers import *

# We know that we'll get back collisions that should match, but it's ambiguous
# whether or not we get (a, b) or (b, a).  In order to do good asserts, we need to make sure
# that we have deterministic sets.  Unlike the basic tests, the manager doesn't
# necessarily always return them in the same order.  to do this, we compare id() and swap the tuples if we have to.
def make_deterministic_set(x):
    ret = set()
    for a, b in x:
        if id(a) <= id(b):
            ret.add((a, b))
        else:
            ret.add((b, a))
    return ret


class ManagerTest(RuleBasedStateMachine):
    boxes = Bundle("boxes")

    def __init__(self):
        super().__init__()
        self.manager = box_manager.BoxManager()
        self.current_boxes = set()

    @rule(target=boxes, new_boxes=BOXES_ST)
    def add_boxes(self, new_boxes):
        for b in new_boxes:
            self.manager.register(b)
            self.current_boxes.add(b)
            assert b.manager is not None
        return multiple(*new_boxes)

    @rule(to_remove=consumes(boxes))
    def remove_box(self, to_remove):
        self.manager.remove(to_remove)
        assert to_remove in self.current_boxes
        self.current_boxes.remove(to_remove)
        assert to_remove.manager is None
        if to_remove.stationary:
            assert not self.manager.stationary_cache_valid

    @rule(
        box=boxes,
        new_x=st.floats(min_value=-100.0, max_value=100.0),
        new_y=st.floats(min_value=-100.0, max_value=100.0),
    )
    def move_box(self, box, new_x, new_y):
        box.move(new_x, new_y)
        assert box.manager is not None
        if box.stationary:
            assert not self.manager.stationary_cache_valid

    @invariant()
    def check_box_collisions(self):
        all_boxes = list(self.current_boxes)
        good = list(base_algorithms.check_deduplicated(all_boxes))
        # We run this one twice, so that the first one has a chance to cache the stationary boxes.
        # Then we check all 3 of them.
        unknown_precached = list(self.manager.yield_collisions())
        unknown_cached = list(self.manager.yield_collisions())
        good_s = make_deterministic_set(good)
        unknown_precached_s = make_deterministic_set(unknown_precached)
        unknown_cached_s = make_deterministic_set(unknown_cached)
        assert len(good_s.intersection(unknown_precached_s)) == len(good_s)
        assert len(good_s.intersection(unknown_cached_s)) == len(good_s)


test_manager = ManagerTest.TestCase