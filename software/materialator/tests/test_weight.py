from materialator.get_weight import get_weight

def test_weight():
    assert get_weight("somefile.stl","9ct gold") > 0.0