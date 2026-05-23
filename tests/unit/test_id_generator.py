from backend.core.id_generator import IdGenerator


def test_id_generator_returns_increasing_bigints() -> None:
    generator = IdGenerator(machine_id=1)

    first = generator.next_id()
    second = generator.next_id()

    assert isinstance(first, int)
    assert isinstance(second, int)
    assert second > first


def test_id_generator_does_not_duplicate_under_burst() -> None:
    """More than 4096 IDs in one millisecond must not produce duplicates."""

    class _BurstClock:
        def __init__(self) -> None:
            self._call_count = 0

        def __call__(self) -> int:
            self._call_count += 1
            # Stay in ms 0 for all 4096 normal-path calls plus the first
            # read of the 4097th call, then advance so the spin-loop exits.
            if self._call_count <= 4097:
                return 0
            return self._call_count

    generator = IdGenerator(machine_id=1, time_provider=_BurstClock())

    ids = {generator.next_id() for _ in range(5000)}
    assert len(ids) == 5000
