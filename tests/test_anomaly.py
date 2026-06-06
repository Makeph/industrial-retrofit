from retrofit.anomaly import EwmaTrend, RollingZScore


def test_zscore_flags_spike_not_noise():
    det = RollingZScore(window=30, k=4.0)
    flagged = []
    for i in range(60):
        x = 1.0 if i != 45 else 9.0   # one clear spike
        anom, _z = det.update(x)
        if anom:
            flagged.append(i)
    assert flagged == [45]


def test_zscore_warmup_is_silent():
    det = RollingZScore(window=30, k=4.0)
    # During warm-up no detection should fire even on varied input.
    assert all(not det.update(v)[0] for v in (0, 5, 1, 4, 2))


def test_ewma_alarms_on_sustained_drift():
    det = EwmaTrend(alpha=0.1, alarm=2.5)
    fired_at = None
    for i in range(200):
        level = 0.6 + i * 0.02          # slow upward drift (bearing wear)
        alarm, _v = det.update(level)
        if alarm and fired_at is None:
            fired_at = i
    assert fired_at is not None
    # must not alarm immediately, only after the trend builds
    assert fired_at > 30
