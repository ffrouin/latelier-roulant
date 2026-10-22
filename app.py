"""Serveur HTTP local pour L’Atelier Roulant."""

import json
import smtplib
import textwrap
import uuid
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from os import environ
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PORT = int(environ.get("PORT", "8000"))
OWNER_EMAIL = environ.get("OWNER_EMAIL", "freddy@linuxtribe.fr")
SMTP_HOST = environ.get("SMTP_HOST", "cgpro.linuxtribe.fr")
SMTP_USERNAME = environ.get("SMTP_USERNAME", OWNER_EMAIL)


def make_pdf(data):
    """Build a small one-page PDF without requiring a third-party package."""
    fields = [
        ("Demande", data.get("service")),
        ("Objet ou équipement", data.get("object")),
        ("Description", data.get("description")),
        ("Lieu", data.get("location")),
        ("Accès particulier", data.get("access")),
        ("Disponibilité", data.get("availability")),
        ("Urgence", data.get("urgency")),
        ("Nom et prénom", f"{data.get('firstname', '')} {data.get('lastname', '')}".strip()),
        ("Téléphone", data.get("phone")),
        ("Photo jointe", data.get("photo_name") or "Aucune photo ajoutée"),
    ]
    lines = ["L'ATELIER ROULANT", "Réparer plutôt que remplacer", "Synthèse de la demande", ""]
    for label, value in fields:
        value = str(value or "Non précisé")
        wrapped = textwrap.wrap(value, width=82) or ["Non précisé"]
        lines.append(f"{label} : {wrapped[0]}")
        lines.extend(f"    {line}" for line in wrapped[1:])
        lines.append("")
    lines.append(f"Référence : {data['request_id']}")

    page_height = 842
    line_height = 16
    content_lines = ["BT", "/F1 16 Tf", "50 790 Td"]
    for index, line in enumerate(lines):
        if index == 1:
            content_lines.append("/F1 11 Tf")
        if index == 2:
            content_lines.append("/F1 14 Tf")
        if index > 2 and line and index != 3:
            content_lines.append("/F1 10 Tf")
        encoded = line.encode("cp1252", "replace").hex()
        content_lines.append(f"<{encoded}> Tj")
        content_lines.append(f"0 -{line_height} Td")
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def send_request_email(data, pdf_bytes):
    """Send the request PDF through the SMTP settings supplied by the host."""
    missing = [name for name in ("SMTP_PASSWORD",) if not environ.get(name)]
    if missing:
        raise RuntimeError(f"Configuration SMTP manquante : {', '.join(missing)}")

    message = EmailMessage()
    message["From"] = environ.get("SMTP_FROM", SMTP_USERNAME)
    message["To"] = OWNER_EMAIL
    message["Subject"] = f"Nouvelle demande de service — {data['request_id']}"
    message.set_content(
        "Bonjour,\n\n"
        f"Une nouvelle demande a été confirmée par {data['firstname']} {data['lastname']}.\n"
        f"Référence : {data['request_id']}\n\n"
        "La synthèse complète est jointe à ce courriel.\n"
    )
    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"demande-{data['request_id']}.pdf",
    )

    host = SMTP_HOST
    port = int(environ.get("SMTP_PORT", "587"))
    if environ.get("SMTP_SSL", "0").lower() in {"1", "true", "yes"}:
        with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
            smtp.login(SMTP_USERNAME, environ["SMTP_PASSWORD"])
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if environ.get("SMTP_STARTTLS", "1").lower() not in {"0", "false", "no"}:
                smtp.starttls()
            smtp.login(SMTP_USERNAME, environ["SMTP_PASSWORD"])
            smtp.send_message(message)


class SiteHandler(SimpleHTTPRequestHandler):
    """Sert les fichiers statiques du site depuis le dépôt."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_POST(self):
        if urlparse(self.path).path != "/api/submit-request":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 200_000:
                raise ValueError("Requête trop volumineuse")
            data = json.loads(self.rfile.read(length))
            required = ("service", "firstname", "lastname", "phone", "town", "availability")
            if not all(str(data.get(field, "")).strip() for field in required):
                raise ValueError("Champs obligatoires manquants")
            if not data.get("human_confirmed"):
                raise ValueError("Confirmation humaine manquante")
            data["request_id"] = uuid.uuid4().hex[:12].upper()
            data["location"] = ", ".join(
                value for value in (data.get("address"), data.get("postcode"), data.get("town")) if value
            )
            pdf_bytes = make_pdf(data)
            send_request_email(data, pdf_bytes)
            self.respond_pdf(200, pdf_bytes, data["request_id"])
        except (ValueError, json.JSONDecodeError) as error:
            self.respond_json(400, {"ok": False, "error": str(error)})
        except Exception as error:  # SMTP errors must reach the browser clearly.
            self.respond_json(503, {"ok": False, "error": str(error)})

    def respond_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_pdf(self, status, body, request_id):
        self.send_response(status)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f"inline; filename=demande-{request_id}.pdf")
        self.send_header("X-Request-ID", request_id)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), SiteHandler)
    print(f"L’Atelier Roulant est disponible sur http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.server_close()
