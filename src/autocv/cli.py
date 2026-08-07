"""Interface en ligne de commande : `autocv build | check | send`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .mailer import DEFAULT_BODY, DEFAULT_SUBJECT, SmtpConfigError
from .mailer import send as send_email
from .models import MissingEnvVarError, load_cv
from .render import build_pdf

DEFAULT_DATA = Path("data/cv.yaml")
DEFAULT_OUTPUT = Path("build/cv.pdf")


def _add_data_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--data", type=Path, default=DEFAULT_DATA, help="fichier YAML du CV")
    sub.add_argument(
        "--strict-env",
        action="store_true",
        help="échouer si une variable ${...} du YAML est absente de l'environnement",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autocv", description="Génère et envoie le CV en PDF.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="compile le CV en PDF")
    _add_data_args(build)
    build.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help="PDF de sortie")
    build.add_argument(
        "--keep-typ", action="store_true", help="conserver la source Typst à côté du PDF"
    )

    check = subparsers.add_parser("check", help="valide le YAML sans produire de PDF")
    _add_data_args(check)

    send = subparsers.add_parser("send", help="envoie le CV par email")
    _add_data_args(send)
    send.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help="PDF de sortie")
    send.add_argument(
        "--pdf",
        type=Path,
        help="envoyer ce PDF existant au lieu d'en compiler un (le YAML n'est pas lu)",
    )
    send.add_argument("--subject", default=DEFAULT_SUBJECT)
    send.add_argument("--body", default=DEFAULT_BODY)
    send.add_argument(
        "--dry-run", action="store_true", help="composer l'email sans se connecter au SMTP"
    )

    return parser


def _load(args: argparse.Namespace):
    """Charge le YAML en traduisant les erreurs en message court sur stderr."""
    try:
        return load_cv(args.data, strict_env=args.strict_env)
    except (OSError, ValueError, MissingEnvVarError) as exc:
        print(f"autocv: {exc}", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "check":
        cv = _load(args)
        if cv is None:
            return 2
        print(
            f"{args.data} valide : {len(cv.experience)} expériences, {len(cv.skills)} compétences"
        )
        return 0

    if args.command == "build":
        cv = _load(args)
        if cv is None:
            return 2
        print(f"PDF généré : {build_pdf(cv, args.output, keep_typ=args.keep_typ)}")
        return 0

    # send
    if args.pdf is not None:
        pdf = args.pdf
        if not pdf.is_file():
            print(f"autocv: PDF introuvable : {pdf}", file=sys.stderr)
            return 2
    else:
        cv = _load(args)
        if cv is None:
            return 2
        pdf = build_pdf(cv, args.output)
        print(f"PDF généré : {pdf}")

    try:
        message = send_email(pdf, subject=args.subject, body=args.body, dry_run=args.dry_run)
    except (SmtpConfigError, OSError) as exc:
        print(f"autocv: envoi impossible : {exc}", file=sys.stderr)
        return 3

    action = "Email composé (dry-run)" if args.dry_run else "Email envoyé"
    print(f"{action} : {message['To']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
