from rapidfuzz import fuzz


def test_fuzz():
    ratio = fuzz.ratio("test", "test")
    print(f"Fuzz ratio for 'test' vs 'test': {ratio}")
    assert ratio == 100

    partial_ratio = fuzz.partial_ratio("test", "testing")
    print(f"Partial ratio for 'test' vs 'testing': {partial_ratio}")
    assert partial_ratio == 100


if __name__ == "__main__":
    test_fuzz()
    print("Smoke test passed!")
