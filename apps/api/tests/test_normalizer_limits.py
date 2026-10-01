import pytest
from app.mappers.normalizer import norm_date, norm_number


def test_huge_numbers_are_rejected_not_inf():
    with pytest.raises(ValueError):
        norm_number("1" + "0" * 400)
    assert norm_number("1" + "0" * 15) == 1e15  # large but finite stays valid


@pytest.mark.parametrize("raw,iso", [
    ("02/06/2026 14:30", "2026-06-02"),
    ("02/06/2026 14:30:00", "2026-06-02"),
    ("2026-05-02 10:30:00", "2026-05-02"),
    ("2026-05-02T10:30:00Z", "2026-05-02"),
])
def test_date_with_time_part(raw, iso):
    assert norm_date(raw) == iso


@pytest.mark.parametrize("raw", ["Tuesday", "soon", "2026-13-45 10:00", "14:30"])
def test_garbage_dates_still_rejected(raw):
    with pytest.raises(ValueError):
        norm_date(raw)