# cv-update-cicd

CV maintenu comme du code : le contenu vit dans un YAML, le PDF est généré par une commande
Python, et la CI le reconstruit et l'envoie par email à chaque push sur `main`.

La chaîne est entièrement Python : pas de R, pas de Quarto, pas de LaTeX à installer.

```text
data/cv.yaml  ──►  Jinja2  ──►  Typst  ──►  CV.pdf  ──►  email (SMTP)
```

## Prérequis

[uv](https://docs.astral.sh/uv/) uniquement. Tout le reste, y compris le moteur de rendu
Typst et les polices, est installé par `uv sync`.

```bash
uv sync
```

## Utilisation

```bash
uv run autocv check                       # valide data/cv.yaml
uv run autocv build                       # écrit build/cv.pdf
uv run autocv build -o CV.pdf --keep-typ  # conserve aussi la source Typst générée
uv run autocv send --dry-run              # compose l'email sans l'envoyer
uv run autocv send                        # compile puis envoie
uv run autocv send --pdf build/cv.pdf     # envoie un PDF déjà construit
```

Mettre à jour le CV = éditer [data/cv.yaml](data/cv.yaml). Rien d'autre à toucher : le texte y
est écrit en clair, sans balisage ni caractères à échapper.

## Variables d'environnement

Les `${VAR}` du YAML sont résolus au chargement. Sans elles, le rendu local produit un PDF
avec les champs concernés vides ; `--strict-env` fait échouer la commande à la place.

| Variable | Usage |
| --- | --- |
| `VILLE`, `TEL` | Coordonnées, volontairement hors du dépôt |
| `SMTP_SERVER`, `SMTP_PORT` | Serveur d'envoi (port 587 : STARTTLS, sinon SSL implicite) |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Authentification SMTP |
| `SMTP_SENDER` | Expéditeur, si différent de `SMTP_USERNAME` (optionnel) |
| `RECIPIENT_EMAIL` | Destinataires, séparés par des virgules |

Rendu local complet :

```bash
VILLE="Paris" TEL="+33 6 00 00 00 00" uv run autocv build
```

## Développement

```bash
uv run pytest
uv run ruff check . && uv run ruff format .
```

## CI

[.github/workflows/render-cv.yml](.github/workflows/render-cv.yml) : lint, tests, rendu du PDF
en artefact, puis envoi par email. L'envoi n'a lieu que sur `main` (jamais depuis une pull
request) et peut être déclenché à la demande via *Run workflow*.

## Mise en forme

Le style reprend celui de l'extension Quarto
[PrettyPDF](https://github.com/nrennie/PrettyPDF) de Nicola Rennie, porté en Typst dans
[src/autocv/templates/cv.typ.j2](src/autocv/templates/cv.typ.j2). Les couleurs, marges, police
et logo se règlent depuis la clé `theme` de `data/cv.yaml`.
