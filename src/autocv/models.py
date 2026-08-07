"""Schéma du CV et chargement du YAML.

Le contenu du CV vit dans `data/cv.yaml`. Les valeurs sensibles (ville, téléphone) ne sont
pas versionnées : elles s'écrivent `${VILLE}` dans le YAML et sont résolues depuis
l'environnement au chargement.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class MissingEnvVarError(RuntimeError):
    """Une variable `${...}` du YAML n'est pas définie dans l'environnement."""


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Contact(_Base):
    city: str = ""
    phone: str = ""
    email: str = ""
    linkedin: str = ""
    github: str = ""


class SkillGroup(_Base):
    label: str
    text: str = ""
    items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _exactly_one_body(self) -> SkillGroup:
        if bool(self.text) == bool(self.items):
            raise ValueError(f"compétence {self.label!r} : renseigner soit 'text', soit 'items'")
        return self


class Experience(_Base):
    period: str
    role: str
    company: str
    location: str = ""
    mission: str = ""
    achievements: list[str] = Field(default_factory=list)


class Education(_Base):
    degree: str
    institution: str = ""
    location: str = ""
    year: str = ""


class Theme(_Base):
    """Équivalent des `\\definecolor` et réglages de l'ancienne extension PrettyPDF."""

    accent: str = "77B5FE"
    light: str = "E6E6FA"
    highlight: str = "800080"
    font: str = "Ubuntu"
    font_size: str = "10pt"
    # Corps de la ligne de titre. Le baisser évite qu'un intitulé de poste long ne passe
    # sur deux lignes et ne fasse déborder le CV.
    heading_size: str = "19pt"
    # Bandeau lavande sur le bord droit. L'ancien PrettyPDF.tex le laissait à 0cm ;
    # passer à 30mm pour retrouver le bandeau d'origine de l'extension.
    sidebar_width: str = "0mm"
    logo: bool = True
    logo_width: str = "15mm"
    margin_x: str = "10mm"
    margin_top: str = "10mm"
    margin_bottom: str = "12mm"


class CV(_Base):
    name: str
    title: str = ""
    tagline: str = ""
    contact: Contact = Field(default_factory=Contact)
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)
    theme: Theme = Field(default_factory=Theme)

    def label(self, key: str, default: str) -> str:
        """Libellé d'interface (titres de sections, préfixes), surchargeable dans le YAML."""
        return self.labels.get(key, default)


def expand_env(value: Any, *, strict: bool = False, env: dict[str, str] | None = None) -> Any:
    """Remplace récursivement les `${VAR}` par leur valeur d'environnement.

    En mode strict une variable absente lève `MissingEnvVarError` ; sinon elle est remplacée
    par une chaîne vide (utile pour un rendu local sans les secrets).
    """
    environ = os.environ if env is None else env

    if isinstance(value, str):

        def substitute(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in environ:
                if strict:
                    raise MissingEnvVarError(f"variable d'environnement manquante : {name}")
                return ""
            return environ[name]

        return _ENV_PATTERN.sub(substitute, value)
    if isinstance(value, dict):
        return {k: expand_env(v, strict=strict, env=env) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v, strict=strict, env=env) for v in value]
    return value


def load_cv(path: str | Path, *, strict_env: bool = False) -> CV:
    """Charge et valide `data/cv.yaml`."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} : le document YAML doit être un mapping")
    return CV.model_validate(expand_env(raw, strict=strict_env))
