import math

from retrofit.oee import OeeAccumulator, availability, oee, performance, quality


def test_textbook_oee():
    # Classic worked example: 480 min planned, 420 run, 1s ideal cycle nonsense aside,
    # 400 parts in 420s at 1s ideal, 380 good.
    a = availability(420, 480)
    p = performance(400, 1.0, 420)
    q = quality(380, 400)
    assert math.isclose(a, 0.875, abs_tol=1e-9)
    assert math.isclose(p, 400 / 420, abs_tol=1e-9)
    assert math.isclose(q, 0.95, abs_tol=1e-9)
    assert math.isclose(oee(420, 480, 400, 380, 1.0), a * p * q, abs_tol=1e-9)


def test_bounds_and_zero_guards():
    assert availability(600, 480) == 1.0          # clamped
    assert performance(10_000, 1.0, 10) == 1.0    # clamped
    assert quality(0, 0) == 0.0
    assert performance(5, 1.0, 0) == 0.0


def test_accumulator_snapshot():
    acc = OeeAccumulator(ideal_cycle_s=2.0)
    for i in range(100):
        acc.tick(running=True, total_count=i + 1, good_count=i + 1, dt_s=2.0)
    snap = acc.snapshot()
    assert snap["availability"] == 1.0
    assert snap["quality"] == 1.0
    assert 0.0 < snap["oee"] <= 1.0
