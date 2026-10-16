from export import to_csv

def test_to_csv_roundtrip():
    assert to_csv([[1, "a"], [2, "b"]]).strip().splitlines() == ["1,a", "2,b"]
