import pytest
from pydantic import ValidationError

from autocv.models import CV, MissingEnvVarError, expand_env, load_cv


def test_expand_env_substitue_les_variables():
    data = {"contact": {"city": "${VILLE}", "phone": "tel ${TEL}"}, "keep": [1, "${VILLE}"]}
    result = expand_env(data, env={"VILLE": "Paris", "TEL": "0102"})
    assert result == {"contact": {"city": "Paris", "phone": "tel 0102"}, "keep": [1, "Paris"]}


def test_expand_env_vide_la_variable_absente_en_mode_souple():
    assert expand_env("[${ABSENT}]", env={}) == "[]"


def test_expand_env_strict_signale_la_variable_absente():
    with pytest.raises(MissingEnvVarError, match="ABSENT"):
        expand_env("${ABSENT}", strict=True, env={})


def test_skill_refuse_text_et_items_simultanes():
    with pytest.raises(ValidationError, match="text"):
        CV.model_validate({"name": "X", "skills": [{"label": "L", "text": "a", "items": ["b"]}]})


def test_skill_refuse_un_groupe_vide():
    with pytest.raises(ValidationError):
        CV.model_validate({"name": "X", "skills": [{"label": "L"}]})


def test_champ_inconnu_rejete():
    with pytest.raises(ValidationError, match="typo"):
        CV.model_validate({"name": "X", "typo": 1})


def test_label_utilise_le_defaut_puis_la_surcharge():
    cv = CV.model_validate({"name": "X", "labels": {"skills": "Skills"}})
    assert cv.label("skills", "Compétences") == "Skills"
    assert cv.label("education", "Formation") == "Formation"


def test_le_cv_du_depot_est_valide(cv_yaml, monkeypatch):
    monkeypatch.setenv("VILLE", "Paris")
    monkeypatch.setenv("TEL", "0102030405")
    cv = load_cv(cv_yaml, strict_env=True)
    assert cv.contact.city == "Paris"
    assert cv.contact.phone == "0102030405"
    assert cv.experience and cv.skills and cv.education


def test_strict_env_echoue_sans_les_secrets(cv_yaml, monkeypatch):
    monkeypatch.delenv("VILLE", raising=False)
    monkeypatch.delenv("TEL", raising=False)
    with pytest.raises(MissingEnvVarError):
        load_cv(cv_yaml, strict_env=True)
