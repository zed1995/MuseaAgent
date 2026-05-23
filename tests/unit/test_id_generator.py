from backend.core.id_generator import IdGenerator


def test_id_generator_returns_increasing_bigints() -> None:
    generator = IdGenerator(machine_id=1)

    first = generator.next_id()
    second = generator.next_id()

    assert isinstance(first, int)
    assert isinstance(second, int)
    assert second > first
