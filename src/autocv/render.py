"""Rendu du CV : YAML -> Typst -> PDF.

Le template Jinja2 produit un document Typst, compilé par `typst-py` (pas de binaire externe,
pas de LaTeX). Toute valeur issue du YAML est injectée sous forme de littéral de chaîne Typst
via le filtre `tq`, ce qui évite d'avoir à échapper les caractères de balisage (`#`, `@`, `*`...).
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import typst
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .models import CV

TEMPLATE_NAME = "cv.typ.j2"


def package_path(*parts: str) -> Path:
    """Chemin d'une ressource embarquée dans le package."""
    return Path(str(resources.files("autocv").joinpath(*parts)))


def typst_quote(value: object) -> str:
    """Rend `value` sous forme de littéral de chaîne Typst."""
    text = "" if value is None else str(value)
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
        .replace("\t", " ")
    )
    return f'"{escaped}"'


@dataclass(frozen=True)
class ContactPart:
    label: str
    value: str
    href: str | None = None


def _contact_lines(cv: CV) -> list[list[ContactPart]]:
    """Les deux lignes de contact sous le titre, en sautant les champs vides."""
    contact = cv.contact
    first = [
        ContactPart(cv.label("city", "Ville :"), contact.city),
        ContactPart(cv.label("phone", "Tél :"), contact.phone),
        ContactPart(cv.label("email", "Email :"), contact.email, f"mailto:{contact.email}"),
    ]
    second = [
        ContactPart(cv.label("linkedin", "LinkedIn :"), contact.linkedin, contact.linkedin),
        ContactPart(cv.label("github", "Github :"), contact.github, contact.github),
    ]
    return [
        line for line in ([p for p in first if p.value], [p for p in second if p.value]) if line
    ]


def _join(parts: list[str], sep: str = " – ") -> str:
    return sep.join(p for p in parts if p)


def build_context(cv: CV) -> dict:
    """Prépare les données déjà mises en forme pour le template."""
    return {
        "cv": cv,
        "theme": cv.theme,
        "sidebar": cv.theme.sidebar_width not in ("", "0mm", "0cm", "0pt", "0"),
        "logo_file": "logo.png",
        "heading": _join([cv.name, cv.title], " | "),
        "contact_lines": _contact_lines(cv),
        "jobs": [
            {
                "period": job.period,
                "heading": _join([job.role, job.company, job.location]),
                "mission": job.mission,
                "achievements": job.achievements,
            }
            for job in cv.experience
        ],
        "education_lines": [
            {
                "degree": edu.degree,
                "rest": _join([edu.institution, edu.location, edu.year], " - "),
            }
            for edu in cv.education
        ],
        "labels": {
            "skills": cv.label("skills", "Compétences"),
            "experience": cv.label("experience", "Expérience Professionnelle"),
            "education": cv.label("education", "Formation"),
            "achievements": cv.label("achievements", "Réalisations Clés :"),
        },
    }


def render_typst(cv: CV, *, template_dir: Path | None = None) -> str:
    """Produit la source Typst du CV."""
    directory = template_dir or package_path("templates")
    env = Environment(
        loader=FileSystemLoader(str(directory)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["tq"] = typst_quote
    return env.get_template(TEMPLATE_NAME).render(**build_context(cv))


def build_pdf(
    cv: CV,
    output: str | Path,
    *,
    template_dir: Path | None = None,
    keep_typ: bool = False,
) -> Path:
    """Compile le CV en PDF et renvoie le chemin produit.

    La compilation se fait dans un répertoire temporaire qui sert de racine Typst : seuls le
    document généré et le logo y sont visibles.
    """
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    source = render_typst(cv, template_dir=template_dir)

    with tempfile.TemporaryDirectory(prefix="autocv-") as tmp:
        root = Path(tmp)
        typ_file = root / "cv.typ"
        typ_file.write_text(source, encoding="utf-8")
        if cv.theme.logo:
            shutil.copyfile(package_path("assets", "logo.png"), root / "logo.png")

        typst.compile(
            input=str(typ_file),
            output=str(output),
            root=str(root),
            font_paths=[str(package_path("assets", "fonts"))],
            ignore_system_fonts=True,
        )

        if keep_typ:
            shutil.copyfile(typ_file, output.with_suffix(".typ"))

    return output
