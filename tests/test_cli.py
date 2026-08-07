import pytest

from autocv.cli import main

SMTP_ENV = {
    "SMTP_SERVER": "smtp.example.org",
    "SMTP_PORT": "465",
    "SMTP_USERNAME": "moi@example.org",
    "SMTP_PASSWORD": "secret",
    "RECIPIENT_EMAIL": "rh@example.org",
}


@pytest.fixture
def smtp_env(monkeypatch):
    for key, value in SMTP_ENV.items():
        monkeypatch.setenv(key, value)


def test_check_valide_le_cv_du_depot(cv_yaml, capsys):
    assert main(["check", "--data", str(cv_yaml)]) == 0
    assert "valide" in capsys.readouterr().out


def test_check_strict_env_echoue_sans_secret(cv_yaml, monkeypatch, capsys):
    monkeypatch.delenv("VILLE", raising=False)
    assert main(["check", "--data", str(cv_yaml), "--strict-env"]) == 2
    assert "VILLE" in capsys.readouterr().err


def test_build_ecrit_le_pdf(cv_yaml, tmp_path):
    output = tmp_path / "out" / "cv.pdf"
    assert main(["build", "--data", str(cv_yaml), "--output", str(output)]) == 0
    assert output.is_file()


def test_build_signale_un_yaml_absent(tmp_path, capsys):
    assert main(["build", "--data", str(tmp_path / "absent.yaml")]) == 2
    assert "autocv:" in capsys.readouterr().err


def test_send_dry_run_reutilise_un_pdf_existant(tmp_path, smtp_env, capsys):
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")

    assert main(["send", "--pdf", str(pdf), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "rh@example.org" in out
    assert "PDF généré" not in out  # aucune recompilation


def test_send_signale_un_pdf_absent(tmp_path, smtp_env, capsys):
    assert main(["send", "--pdf", str(tmp_path / "absent.pdf")]) == 2
    assert "introuvable" in capsys.readouterr().err


def test_send_signale_une_config_smtp_incomplete(tmp_path, monkeypatch, capsys):
    for key in SMTP_ENV:
        monkeypatch.delenv(key, raising=False)
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")

    assert main(["send", "--pdf", str(pdf)]) == 3
    assert "SMTP_SERVER" in capsys.readouterr().err
