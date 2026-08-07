from pathlib import Path

import pytest

from autocv.models import CV

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cv_yaml() -> Path:
    """Le CV réellement versionné dans le dépôt."""
    return REPO_ROOT / "data" / "cv.yaml"


@pytest.fixture
def minimal_cv() -> CV:
    return CV.model_validate(
        {
            "name": "Ada Lovelace",
            "title": "Analyst",
            "tagline": "Notes sur la machine analytique",
            "contact": {"city": "Londres", "email": "ada@example.org"},
            "skills": [{"label": "Maths", "text": "Algorithmes"}],
            "experience": [
                {
                    "period": "1842 – 1843",
                    "role": "Traductrice",
                    "company": "Menabrea",
                    "mission": "Notes sur la machine analytique.",
                    "achievements": ["Premier algorithme publié."],
                }
            ],
            "education": [{"degree": "Mathématiques", "year": "1840"}],
        }
    )
