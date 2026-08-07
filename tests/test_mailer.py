import pytest

from autocv.mailer import SmtpConfig, SmtpConfigError, build_message, send

ENV = {
    "SMTP_SERVER": "smtp.example.org",
    "SMTP_PORT": "465",
    "SMTP_USERNAME": "moi@example.org",
    "SMTP_PASSWORD": "secret",
    "RECIPIENT_EMAIL": "rh@example.org",
}


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "cv.pdf"
    path.write_bytes(b"%PDF-1.7\n%%EOF\n")
    return path


def test_from_env_lit_la_configuration():
    config = SmtpConfig.from_env(ENV)
    assert config.host == "smtp.example.org"
    assert config.port == 465
    assert config.sender == "moi@example.org"
    assert config.recipients == ("rh@example.org",)
    assert config.use_ssl is True


def test_port_587_bascule_en_starttls():
    assert SmtpConfig.from_env({**ENV, "SMTP_PORT": "587"}).use_ssl is False


def test_destinataires_multiples():
    config = SmtpConfig.from_env({**ENV, "RECIPIENT_EMAIL": "a@x.org, b@x.org"})
    assert config.recipients == ("a@x.org", "b@x.org")


def test_expediteur_surchargeable():
    assert SmtpConfig.from_env({**ENV, "SMTP_SENDER": "cv@x.org"}).sender == "cv@x.org"


def test_variables_manquantes_listees():
    incomplete = {k: v for k, v in ENV.items() if k != "SMTP_PASSWORD"}
    with pytest.raises(SmtpConfigError, match="SMTP_PASSWORD"):
        SmtpConfig.from_env(incomplete)


def test_port_non_numerique_rejete():
    with pytest.raises(SmtpConfigError, match="SMTP_PORT"):
        SmtpConfig.from_env({**ENV, "SMTP_PORT": "ssl"})


def test_message_porte_le_pdf_en_piece_jointe(pdf):
    message = build_message(SmtpConfig.from_env(ENV), pdf, subject="CV")
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "cv.pdf"
    assert attachments[0].get_content_type() == "application/pdf"
    assert message["Subject"] == "CV"


def test_piece_jointe_absente_signalee(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_message(SmtpConfig.from_env(ENV), tmp_path / "absent.pdf")


def test_dry_run_n_ouvre_aucune_connexion(pdf, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("aucune connexion SMTP ne doit être ouverte en dry-run")

    monkeypatch.setattr("smtplib.SMTP_SSL", interdit)
    monkeypatch.setattr("smtplib.SMTP", interdit)

    message = send(pdf, config=SmtpConfig.from_env(ENV), dry_run=True)
    assert message["To"] == "rh@example.org"
