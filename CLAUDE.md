# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Vue d'ensemble

CV personnel (Lewis Hounkpevi, en français) généré par une chaîne 100% Python :
`data/cv.yaml` -> Jinja2 -> document Typst -> PDF via `typst-py` -> envoi SMTP. Aucune
dépendance système : pas de R, pas de Quarto, pas de LaTeX. Le "produit" est le PDF.

Le projet a été migré depuis une chaîne Quarto/R/TinyTeX ; l'historique git contient encore
les `.qmd` et l'extension `_extensions/nrennie/PrettyPDF` si besoin de référence.

## Commandes

```bash
uv sync                                   # environnement complet
uv run autocv check                       # valide data/cv.yaml
uv run autocv build                       # build/cv.pdf
uv run autocv build --keep-typ            # + la source Typst générée, pour déboguer le rendu
uv run autocv send --dry-run              # compose l'email sans connexion SMTP
uv run pytest
uv run pytest tests/test_render.py::test_build_pdf_produit_un_pdf_lisible
uv run ruff check . && uv run ruff format .
```

`pytest` est configuré avec `-q` dans `addopts` : pour du verbeux, utiliser
`uv run pytest -o addopts= -v` (un simple `-v` s'annule avec le `-q`).

Rendu local réaliste (sinon ville et téléphone sortent vides) :

```bash
VILLE="Paris" TEL="+33 6 00 00 00 00" uv run autocv build
```

## Architecture

- [data/cv.yaml](data/cv.yaml) : **tout le contenu du CV**, plus une clé `theme` (couleurs,
  marges, police, logo). C'est le seul fichier à toucher pour une mise à jour de contenu.
- [src/autocv/models.py](src/autocv/models.py) : schéma Pydantic (`extra="forbid"`, donc une
  clé inconnue dans le YAML échoue) et `load_cv`. C'est aussi là que les `${VAR}` du YAML sont
  résolus depuis l'environnement, avec un mode `strict` qui lève au lieu de substituer du vide.
- [src/autocv/render.py](src/autocv/render.py) : `build_context` met le contenu en forme
  (assemblage des intitulés, filtrage des champs de contact vides) puis le template produit le
  Typst. `build_pdf` compile dans un répertoire temporaire qui sert de racine Typst.
- [src/autocv/templates/cv.typ.j2](src/autocv/templates/cv.typ.j2) : mise en page, portage du
  style PrettyPDF (accent `#77B5FE`, liens violets, police Ubuntu, logo page 1).
- [src/autocv/mailer.py](src/autocv/mailer.py) : `smtplib` + `EmailMessage`. Le port 587
  déclenche STARTTLS, tout autre port du SMTPS implicite.
- [src/autocv/cli.py](src/autocv/cli.py) : `argparse`, sous-commandes `build` / `check` / `send`.

### Invariant important : injection Typst

Toute valeur issue du YAML entre dans le document via le filtre Jinja `tq`
(`render.typst_quote`), qui produit un **littéral de chaîne Typst** (`#"texte"`). Les
caractères de balisage Typst (`#`, `@`, `*`, `_`, `<`, `>`, `$`) sont donc inertes et le YAML
n'a besoin d'aucun échappement. Ne jamais interpoler une valeur directement dans le balisage
du template : cela réintroduirait le problème (une adresse email deviendrait une référence
Typst `@...`). `tests/test_render.py::test_build_pdf_survit_aux_caracteres_de_balisage`
verrouille ce comportement.

Corollaire : le YAML ne supporte pas le markdown. Le gras et les puces viennent de la
structure des données (`SkillGroup.label` vs `text` / `items`), pas du texte.

### Polices et reproductibilité

La compilation passe `ignore_system_fonts=True` et pointe `font_paths` sur
`src/autocv/assets/fonts`. Le rendu est donc identique en local et en CI. Ajouter une police
au thème suppose d'ajouter le `.ttf` dans ce dossier.

## CI

[.github/workflows/render-cv.yml](.github/workflows/render-cv.yml) : lint, tests, rendu avec
`--strict-env` (un secret manquant fait échouer le build au lieu de publier un CV incomplet),
artefact, puis un **unique** envoi email, conditionné à `push` sur `main` ou à un
`workflow_dispatch` avec `send_email`. Les pull requests construisent sans envoyer.

Secrets attendus : `VILLE`, `TEL`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`,
`SMTP_PASSWORD`, `RECIPIENT_EMAIL`, et `SMTP_SENDER` en option.

`.github/workflows/hide-secrets.yml` est une démo de `::add-mask::` sans rapport avec le CV.

## Données personnelles

Ville et téléphone sont hors du dépôt et injectés par `${VILLE}` / `${TEL}`. Ne jamais les
réintroduire en dur dans `data/cv.yaml`. Le PDF généré (`build/`) n'est pas versionné.
