# tests/test_redact_sample.py
from scripts.redact_sample import redact_text

def test_redacts_email():
    assert redact_text("mail g.schubert@htl-leonding.ac.at now") == \
        "mail redacted@example.org now"

def test_keeps_placeholder_untouched_shape():
    out = redact_text("VORNAME.NACHNAME@students.htl-leonding.ac.at")
    assert out == "redacted@example.org"

def test_no_email_unchanged():
    assert redact_text("no address here") == "no address here"

def test_check_mode_passes_on_clean_text(tmp_path):
    from scripts.redact_sample import scan_for_emails
    assert scan_for_emails("no pii here") == []
    assert scan_for_emails("a@b.co") == ["a@b.co"]
