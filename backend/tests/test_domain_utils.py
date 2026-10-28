from backend.domain_utils import normalize_domain


def test_normalize_domain_canonicalizes_case_spaces_trailing_dot_and_idn():
    assert normalize_domain("  Example.COM. ") == "example.com"
    assert normalize_domain("münich.example") == "xn--mnich-kva.example"


def test_normalize_domain_rejects_invalid_values():
    for value in ["", "example", "example..com", "https://example.com", "-invalid.com"]:
        assert normalize_domain(value) is None
