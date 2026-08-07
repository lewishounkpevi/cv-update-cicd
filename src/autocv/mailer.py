"""Envoi du CV par email (remplace l'étape blastula de l'ancien workflow R)."""

from __future__ import annotations

import mimetypes
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

DEFAULT_SUBJECT = "CV Update"
DEFAULT_BODY = "Bonjour,\n\nVous trouverez ci-joint la dernière version de mon CV.\n"


class SmtpConfigError(RuntimeError):
    """Configuration SMTP incomplète ou invalide."""


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    sender: str
    recipients: tuple[str, ...]
    use_ssl: bool = True

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> SmtpConfig:
        """Lit la configuration depuis les variables d'environnement (secrets GitHub)."""
        environ = os.environ if env is None else env
        missing = [
            name
            for name in (
                "SMTP_SERVER",
                "SMTP_PORT",
                "SMTP_USERNAME",
                "SMTP_PASSWORD",
                "RECIPIENT_EMAIL",
            )
            if not environ.get(name)
        ]
        if missing:
            raise SmtpConfigError(f"variables SMTP manquantes : {', '.join(missing)}")

        raw_port = environ["SMTP_PORT"]
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise SmtpConfigError(f"SMTP_PORT invalide : {raw_port!r}") from exc

        recipients = tuple(
            address.strip() for address in environ["RECIPIENT_EMAIL"].split(",") if address.strip()
        )
        if not recipients:
            raise SmtpConfigError("RECIPIENT_EMAIL ne contient aucune adresse")

        return cls(
            host=environ["SMTP_SERVER"],
            port=port,
            username=environ["SMTP_USERNAME"],
            password=environ["SMTP_PASSWORD"],
            sender=environ.get("SMTP_SENDER") or environ["SMTP_USERNAME"],
            recipients=recipients,
            # Port 587 fait du STARTTLS, 465 du SMTPS implicite.
            use_ssl=port != 587,
        )


def build_message(
    config: SmtpConfig,
    attachment: Path,
    *,
    subject: str = DEFAULT_SUBJECT,
    body: str = DEFAULT_BODY,
) -> EmailMessage:
    """Compose l'email avec le PDF en pièce jointe."""
    if not attachment.is_file():
        raise FileNotFoundError(f"pièce jointe introuvable : {attachment}")

    message = EmailMessage()
    message["From"] = config.sender
    message["To"] = ", ".join(config.recipients)
    message["Subject"] = subject
    message.set_content(body)

    guessed, _ = mimetypes.guess_type(attachment.name)
    maintype, _, subtype = (guessed or "application/octet-stream").partition("/")
    message.add_attachment(
        attachment.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=attachment.name,
    )
    return message


def send(
    attachment: Path,
    *,
    config: SmtpConfig | None = None,
    subject: str = DEFAULT_SUBJECT,
    body: str = DEFAULT_BODY,
    dry_run: bool = False,
) -> EmailMessage:
    """Envoie le CV. En `dry_run`, compose le message sans ouvrir de connexion."""
    config = config or SmtpConfig.from_env()
    message = build_message(config, attachment, subject=subject, body=body)
    if dry_run:
        return message

    context = ssl.create_default_context()
    if config.use_ssl:
        with smtplib.SMTP_SSL(config.host, config.port, context=context) as server:
            server.login(config.username, config.password)
            server.send_message(message)
    else:
        with smtplib.SMTP(config.host, config.port) as server:
            server.starttls(context=context)
            server.login(config.username, config.password)
            server.send_message(message)
    return message
