"""Serveur HTTP local pour L’Atelier Roulant."""

import base64
import io
import json
import re
import shutil
import smtplib
import subprocess
import textwrap
import uuid
import zlib
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
PUBLIC_BASE_URL = environ.get("PUBLIC_BASE_URL", "https://atelier-roulant.linuxtribe.fr").rstrip("/")
REQUEST_STORAGE_DIR = Path(environ.get("REQUEST_STORAGE_DIR", ROOT / "data" / "requests"))


def pdf_text(value):
    return f"<{str(value).encode('cp1252', 'replace').hex()}> Tj"


def add_rgb_image(objects, image_bytes, name):
    """Convert an uploaded/PNG image into a compressed PDF RGB image object."""
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as source:
        source.thumbnail((900, 900))
        image = source.convert("RGB")
        width, height = image.size
        compressed = zlib.compress(image.tobytes(), level=6)
    obj = (
        f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
        f"/Length {len(compressed)} >>\nstream\n"
    ).encode("ascii") + compressed + b"\nendstream"
    objects.append(obj)
    return len(objects)


def qr_png(url):
    """Generate a QR PNG using the host's qrencode command."""
    if not shutil.which("qrencode"):
        raise RuntimeError("Le programme qrencode est requis pour générer le QR code")
    result = subprocess.run(
        ["qrencode", "-t", "PNG", "-o", "-", "-s", "6", "-m", "1", url],
        check=True,
        capture_output=True,
        timeout=5,
    )
    return result.stdout


def decode_photo(data_url):
    if not data_url:
        return None
    if len(data_url) > 5_000_000 or "," not in data_url:
        raise ValueError("Photo trop volumineuse ou invalide")
    _, encoded = data_url.split(",", 1)
    try:
        return base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError("Photo invalide") from error


def wrap_lines(value, width):
    return textwrap.wrap(str(value or "Non précisé"), width=width) or ["Non précisé"]


def make_pdf(data, document_url):
    """Build a branded A4 PDF with customer block, request, photo and QR code."""
    orange = (0.93, 0.42, 0.23)
    ink = (0.09, 0.13, 0.12)
    paper = (0.98, 0.97, 0.94)
    pale_orange = (1.0, 0.94, 0.89)
    muted = (0.34, 0.38, 0.36)

    def fill(color):
        return f"{color[0]} {color[1]} {color[2]} rg"

    def stroke(color):
        return f"{color[0]} {color[1]} {color[2]} RG"

    commands = [
        "q",
        fill(paper), "0 0 595 842 re f",
        fill(ink), "0 770 595 72 re f",
        fill(orange), "42 784 7 45 re f",
        "BT", "/F1 24 Tf", fill((1, 1, 1)), "55 810 Td", pdf_text("L'ATELIER ROULANT"), "ET",
        "BT", "/F1 10 Tf", fill(orange), "55 790 Td", pdf_text("Réparer plutôt que remplacer"), "ET",
        "Q",
    ]

    # Customer details: intentionally no heading, as requested.
    commands += [
        "q", fill(pale_orange), "45 678 505 70 re f", stroke(orange), "45 678 505 70 re S", "Q",
        "BT", "/F1 15 Tf", fill(ink), "62 720 Td", pdf_text(f"{data['firstname']} {data['lastname']}"), "ET",
        "BT", "/F1 11 Tf", fill(ink), "62 697 Td", pdf_text(data["phone"]), "ET",
        "BT", "/F1 10 Tf", fill(muted), "285 720 Td", pdf_text(data.get("location") or "Lieu non précisé"), "ET",
        "BT", "/F1 10 Tf", fill(muted), "285 697 Td", pdf_text(data.get("access") or "Accès non précisé"), "ET",
        "BT", "/F1 18 Tf", fill(orange), "45 645 Td", pdf_text("Votre demande"), "ET",
    ]

    request_fields = [
        ("Besoin", data.get("service")),
        ("Objet ou équipement", data.get("object")),
        ("Description", data.get("description")),
        ("Disponibilité", data.get("availability")),
        ("Urgence", data.get("urgency")),
    ]
    y = 616
    for label, value in request_fields:
        commands += ["BT", "/F1 9 Tf", fill(orange), f"55 {y} Td", pdf_text(label.upper()), "ET"]
        y -= 14
        lines = wrap_lines(value, 55)
        commands += ["BT", "/F1 11 Tf", fill(ink), f"55 {y} Td", pdf_text(lines[0]), "ET"]
        y -= 16
        for line in lines[1:3]:
            commands += ["BT", "/F1 10 Tf", fill(ink), f"65 {y} Td", pdf_text(line), "ET"]
            y -= 14
        y -= 6

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    image_refs = {}
    qr_ref = add_rgb_image(objects, qr_png(document_url), "QR")
    image_refs["QR"] = qr_ref

    photo_bytes = decode_photo(data.get("photo_data"))
    if photo_bytes:
        image_refs["PHOTO"] = add_rgb_image(objects, photo_bytes, "PHOTO")

    # Photo panel on the right-hand side of the request.
    commands += [
        "q", fill((1, 1, 1)), "365 405 165 210 re f", stroke(orange), "365 405 165 210 re S", "Q",
        "BT", "/F1 9 Tf", fill(orange), "378 590 Td", pdf_text("PHOTO JOINTE"), "ET",
    ]
    if "PHOTO" in image_refs:
        commands += [
            "q", "145 0 0 145 375 425 cm", "/PHOTO Do", "Q",
        ]
    else:
        commands += [
            "BT", "/F1 11 Tf", fill(muted), "395 505 Td", pdf_text("Aucune photo"), "ET",
        ]

    commands += [
        "q", fill((1, 1, 1)), "425 65 105 105 re f", stroke(orange), "425 65 105 105 re S", "Q",
        "q", "75 0 0 75 440 80 cm", "/QR Do", "Q",
        "BT", "/F1 9 Tf", fill(orange), "55 125 Td", pdf_text("DOCUMENT EN LIGNE"), "ET",
    ]
    for index, line in enumerate(wrap_lines(document_url, 58)[:3]):
        commands += ["BT", "/F1 8 Tf", fill(muted), f"55 {108 - index * 11} Td", pdf_text(line), "ET"]
    commands += [
        "BT", "/F1 9 Tf", fill(muted), "55 42 Td", pdf_text(f"Référence : {data['request_id']}"), "ET",
    ]
    content = "\n".join(commands).encode("ascii")

    xobjects = " /XObject << " + " ".join(f"/{name} {ref} 0 R" for name, ref in image_refs.items()) + " >>"
    objects[2] = (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        f"/Resources << /Font << /F1 5 0 R >>{xobjects} >> /Contents 4 0 R >>"
    ).encode("ascii")
    objects[3] = (
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream"
    )

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


def send_request_email(data, pdf_bytes, document_url):
    """Send the request PDF only to the backend owner address."""
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
        f"Référence : {data['request_id']}\n"
        f"Document en ligne : {document_url}\n\n"
        "La synthèse complète est jointe à ce courriel.\n"
    )
    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"demande-{data['request_id']}.pdf",
    )

    port = int(environ.get("SMTP_PORT", "587"))
    if environ.get("SMTP_SSL", "0").lower() in {"1", "true", "yes"}:
        with smtplib.SMTP_SSL(SMTP_HOST, port, timeout=20) as smtp:
            smtp.login(SMTP_USERNAME, environ["SMTP_PASSWORD"])
            smtp.send_message(message)
    else:
        with smtplib.SMTP(SMTP_HOST, port, timeout=20) as smtp:
            if environ.get("SMTP_STARTTLS", "1").lower() not in {"0", "false", "no"}:
                smtp.starttls()
            smtp.login(SMTP_USERNAME, environ["SMTP_PASSWORD"])
            smtp.send_message(message)


class SiteHandler(SimpleHTTPRequestHandler):
    """Sert les fichiers statiques et les demandes PDF."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        match = re.fullmatch(r"/requests/([A-F0-9]{12})\.pdf", path)
        if match:
            pdf_path = REQUEST_STORAGE_DIR / f"{match.group(1)}.pdf"
            if not pdf_path.is_file():
                self.send_error(404)
                return
            body = pdf_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f"inline; filename={pdf_path.name}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/submit-request":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 6_000_000:
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
            document_url = f"{PUBLIC_BASE_URL}/requests/{data['request_id']}.pdf"
            pdf_bytes = make_pdf(data, document_url)
            REQUEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            pdf_path = REQUEST_STORAGE_DIR / f"{data['request_id']}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            send_request_email(data, pdf_bytes, document_url)
            self.respond_pdf(200, pdf_bytes, data["request_id"])
        except (ValueError, json.JSONDecodeError) as error:
            self.respond_json(400, {"ok": False, "error": str(error)})
        except Exception as error:  # SMTP/PDF errors must reach the browser clearly.
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
