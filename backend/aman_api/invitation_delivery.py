"""Optional SMTP delivery for one-time organization invitations."""
from __future__ import annotations

import ipaddress
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from urllib.parse import urlencode, urlsplit, urlunsplit


class InvitationEmailConfigurationError(ValueError):
    """Raised when SMTP delivery was requested but its settings are incomplete."""


class InvitationEmailDeliveryError(RuntimeError):
    """Raised when the configured SMTP relay does not accept an invitation."""


@dataclass(frozen=True)
class InvitationEmailConfig:
    host: str
    port: int
    sender: str
    username: str | None
    password: str | None
    tls_mode: str
    timeout_seconds: float
    console_url: str


def _console_url(value: str, environment: str) -> str:
    if value.strip() != value or any(ord(char) < 32 for char in value):
        raise InvitationEmailConfigurationError("AMAN_CONSOLE_URL must be a clean absolute URL")
    try:
        parts = urlsplit(value)
        host = parts.hostname
        _ = parts.port
    except ValueError as exc:
        raise InvitationEmailConfigurationError("AMAN_CONSOLE_URL is invalid") from exc
    if not host or parts.username is not None or parts.password is not None or parts.query or parts.fragment:
        raise InvitationEmailConfigurationError("AMAN_CONSOLE_URL must not contain credentials, query, or fragment")
    scheme = parts.scheme.lower()
    is_loopback = host.lower() == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if scheme != "https" and not (scheme == "http" and is_loopback and environment == "development"):
        raise InvitationEmailConfigurationError("AMAN_CONSOLE_URL must use HTTPS outside local development")
    path = parts.path.rstrip("/")
    if not path.endswith("/admin.html"):
        path = f"{path}/admin.html"
    return urlunsplit((scheme, parts.netloc, path, "", ""))


def load_invitation_email_config() -> InvitationEmailConfig | None:
    """Return None for manual delivery; reject partial or unsafe SMTP configuration."""
    names = (
        "AMAN_EMAIL_SMTP_HOST",
        "AMAN_EMAIL_SMTP_PORT",
        "AMAN_EMAIL_FROM",
        "AMAN_EMAIL_SMTP_USERNAME",
        "AMAN_EMAIL_SMTP_PASSWORD",
        "AMAN_EMAIL_SMTP_TLS_MODE",
        "AMAN_EMAIL_SMTP_TIMEOUT_SECONDS",
        "AMAN_CONSOLE_URL",
    )
    configured = {
        name: os.environ.get(name, "") if name == "AMAN_EMAIL_SMTP_PASSWORD"
        else os.environ.get(name, "").strip()
        for name in names
    }
    if not any(configured.values()):
        return None
    required = ("AMAN_EMAIL_SMTP_HOST", "AMAN_EMAIL_FROM", "AMAN_CONSOLE_URL")
    if any(not configured[name] for name in required):
        raise InvitationEmailConfigurationError("SMTP delivery requires host, sender, and console URL settings")
    username = configured["AMAN_EMAIL_SMTP_USERNAME"] or None
    password = configured["AMAN_EMAIL_SMTP_PASSWORD"] or None
    if bool(username) != bool(password):
        raise InvitationEmailConfigurationError("SMTP username and password must be configured together")
    try:
        port = int(configured["AMAN_EMAIL_SMTP_PORT"] or "587")
        timeout = float(configured["AMAN_EMAIL_SMTP_TIMEOUT_SECONDS"] or "10")
    except ValueError as exc:
        raise InvitationEmailConfigurationError("SMTP port and timeout must be numeric") from exc
    if not 1 <= port <= 65_535 or not 1 <= timeout <= 30:
        raise InvitationEmailConfigurationError("SMTP port or timeout is outside its allowed range")
    tls_mode = (configured["AMAN_EMAIL_SMTP_TLS_MODE"] or "starttls").lower()
    if tls_mode not in {"starttls", "implicit"}:
        raise InvitationEmailConfigurationError("SMTP TLS mode must be starttls or implicit")
    sender = configured["AMAN_EMAIL_FROM"]
    if parseaddr(sender)[1] != sender or "@" not in sender or any(ord(char) < 32 for char in sender):
        raise InvitationEmailConfigurationError("AMAN_EMAIL_FROM must be one email address")
    if any(char.isspace() or ord(char) < 32 for char in configured["AMAN_EMAIL_SMTP_HOST"]):
        raise InvitationEmailConfigurationError("AMAN_EMAIL_SMTP_HOST must not contain whitespace or controls")
    return InvitationEmailConfig(
        host=configured["AMAN_EMAIL_SMTP_HOST"],
        port=port,
        sender=sender,
        username=username,
        password=password,
        tls_mode=tls_mode,
        timeout_seconds=timeout,
        console_url=_console_url(configured["AMAN_CONSOLE_URL"], os.environ.get("AMAN_ENVIRONMENT", "development").lower()),
    )


def send_invitation_email(
    config: InvitationEmailConfig,
    recipient: str,
    organization_name: str,
    role: str,
    token: str,
    expires_at: int,
) -> None:
    """Send a plain-text invitation. The token is never returned or logged here."""
    safe_organization_name = " ".join(
        "".join(char for char in organization_name if ord(char) >= 32 and ord(char) != 127).split()
    )
    invite_url = urlunsplit((
        urlsplit(config.console_url).scheme,
        urlsplit(config.console_url).netloc,
        urlsplit(config.console_url).path,
        "",
        urlencode({"invite": token}),
    ))
    role_label = {"admin": "Administrateur", "editor": "Éditeur", "viewer": "Lecteur"}.get(role)
    if role_label is None or not safe_organization_name:
        raise InvitationEmailDeliveryError("Invitation content is invalid")
    expiry = datetime.fromtimestamp(expires_at, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message = EmailMessage()
    message["Subject"] = f"Invitation ALAMANE - {safe_organization_name}"
    message["From"] = config.sender
    message["To"] = recipient
    message.set_content(
        f"Bonjour,\n\n"
        f"Vous êtes invité(e) à rejoindre l’organisation « {safe_organization_name} » "
        f"avec le rôle « {role_label} ».\n\n"
        f"Ouvrez ce lien pour examiner et accepter l’invitation :\n{invite_url}\n\n"
        f"Le lien à usage unique expire le {expiry}. Si vous ne vous attendiez pas à cette invitation, "
        f"ignorez ce message.\n\nALAMANE\n"
    )
    context = ssl.create_default_context()
    try:
        if config.tls_mode == "implicit":
            server = smtplib.SMTP_SSL(
                config.host, config.port, timeout=config.timeout_seconds, context=context
            )
        else:
            server = smtplib.SMTP(config.host, config.port, timeout=config.timeout_seconds)
        with server:
            server.ehlo()
            if config.tls_mode == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if config.username:
                server.login(config.username, config.password or "")
            refused = server.send_message(message)
            if refused:
                raise InvitationEmailDeliveryError("SMTP relay refused the invitation recipient")
    except InvitationEmailDeliveryError:
        raise
    except Exception as exc:
        raise InvitationEmailDeliveryError("SMTP relay did not accept the invitation") from exc
