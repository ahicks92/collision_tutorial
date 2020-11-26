import hypothesis.strategies as st

from collision_tutorial import box, base_algorithms, test_helpers

_BOX_ST = st.builds(
    box.Box,
    x=st.floats(0.0, 100.0),
    y=st.floats(0.0, 100.0),
    width=st.floats(0.0, 20.0),
    height=st.floats(0.0, 20.0),
    stationary=st.booleans(),
)


def box_hard_case():
    # Two boxes which don't have any corners inside the other. basically, a giant cross.
    return [box.Box(-100.0, 0.0, 200.0, 1.0), box.Box(0.0, -100.0, 1.0, 200.0)]


BOXES_ST = st.builds(box_hard_case) | st.lists(_BOX_ST)