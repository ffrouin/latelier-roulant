"""Serveur HTTP local pour L’Atelier Roulant."""

import base64
import copy
from collections import defaultdict, deque
from datetime import datetime
import hmac
import ipaddress
import importlib
import io
import json
import logging
import os
import re
import shutil
import smtplib
import subprocess
import textwrap
import threading
import time
import tempfile
import uuid
import zlib
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from os import environ
from pathlib import Path
from urllib.parse import urlparse

LOG_LEVEL = environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("latelier-roulant")

APP_HOME = environ.get("APP_HOME")
ROOT = (Path(APP_HOME).expanduser() if APP_HOME else Path(__file__).resolve().parent)
PORT = int(environ.get("PORT", "8000"))
OWNER_EMAIL = environ.get("OWNER_EMAIL", "me@my.mail")
SMTP_HOST = environ.get("SMTP_HOST", "smtp.my.mail")
SMTP_USERNAME = environ.get("SMTP_USERNAME", OWNER_EMAIL)
PUBLIC_BASE_URL = environ.get("PUBLIC_BASE_URL", "https://atelier-roulant.linuxtribe.fr").rstrip("/")
LEGAL_BUSINESS_NAME = environ.get("LEGAL_BUSINESS_NAME", "L'Atelier Roulant")
LEGAL_CONTACT_NAME = environ.get("LEGAL_CONTACT_NAME", "")
LEGAL_PHONE = environ.get("LEGAL_PHONE", "")
LEGAL_REGISTRATION = environ.get("LEGAL_REGISTRATION", "")
LEGAL_EMAIL = environ.get("LEGAL_EMAIL", OWNER_EMAIL)
DEFAULT_REQUEST_STORAGE_DIR = ROOT / "requests" if (ROOT / "requests").is_dir() else ROOT / "data" / "requests"
REQUEST_STORAGE_DIR = Path(environ.get("REQUEST_STORAGE_DIR", str(DEFAULT_REQUEST_STORAGE_DIR)))
REQUEST_REFERENCE_RE = re.compile(r"^(?:[A-F0-9]{12}|[A-F0-9]{32})$")
REQUEST_STATUSES = ("A traiter", "Planifié", "Traité", "Abandon")
ADMIN_USERNAME = environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = environ.get("ADMIN_PASSWORD", "")
GEOIP_DB_PATH = environ.get("GEOIP_DB_PATH", "/usr/share/GeoIP/GeoLite2-City.mmdb")
GEOIP_LEGACY_DB_PATH = environ.get("GEOIP_LEGACY_DB_PATH", "")
def get_commit_reference():
    git_dir = ROOT / ".git"
    LOGGER.info("Recherche du commit: root=%s git=%s existe=%s", ROOT, git_dir, git_dir.exists())
    if git_dir.is_file():
        try:
            git_dir = (ROOT / git_dir.read_text(encoding="utf-8").strip().split(" ", 1)[1]).resolve()
            LOGGER.info("Dépôt Git de worktree détecté: %s", git_dir)
        except (OSError, IndexError, UnicodeError):
            LOGGER.exception("Impossible de lire le fichier .git")
            return "inconnu"
    try:
        git_root = ROOT.resolve()
        commit = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={git_root}",
                "--no-optional-locks",
                "-C",
                str(git_root),
                "rev-parse",
                "--short",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
        if re.fullmatch(r"[0-9a-f]{7,40}", commit):
            LOGGER.info("Commit récupéré avec git: %s", commit)
            return commit
        LOGGER.warning("git a retourné une référence invalide: %r", commit)
    except subprocess.CalledProcessError as error:
        LOGGER.warning(
            "Impossible d'exécuter git (code=%s): %s",
            error.returncode,
            (error.stderr or "").strip() or error,
        )
    except (OSError, subprocess.SubprocessError) as error:
        LOGGER.warning("Impossible d'exécuter git: %s", error)
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        LOGGER.info("Lecture directe de .git/HEAD: %r", head)
        if head.startswith("ref: "):
            ref = head[6:]
            ref_path = git_dir / ref
            if ref_path.is_file():
                commit = ref_path.read_text(encoding="ascii").strip()
                if re.fullmatch(r"[0-9a-f]{7,40}", commit):
                    LOGGER.info("Commit récupéré depuis %s: %s", ref_path, commit[:12])
                    return commit[:12]
            packed_refs = git_dir / "packed-refs"
            if packed_refs.is_file():
                for line in packed_refs.read_text(encoding="ascii").splitlines():
                    if line and not line.startswith("#") and not line.startswith("^"):
                        commit_hash, packed_ref = line.split(" ", 1)
                        if packed_ref == ref and re.fullmatch(r"[0-9a-f]{7,40}", commit_hash):
                            LOGGER.info("Commit récupéré depuis packed-refs: %s", commit_hash[:12])
                            return commit_hash[:12]
        if re.fullmatch(r"[0-9a-f]{7,40}", head):
            LOGGER.info("Commit détaché récupéré depuis HEAD: %s", head[:12])
            return head[:12]
    except (OSError, UnicodeError, ValueError) as error:
        LOGGER.warning("Impossible de lire directement les métadonnées Git: %s", error)
    LOGGER.error("Référence de commit inconnue: dépôt Git absent ou inaccessible")
    return "inconnu"


APP_COMMIT = get_commit_reference()
SERVER_STARTED_AT = time.time()
WEB_STATS_LOCK = threading.Lock()
WEB_STATS = {
    "total_requests": 0,
    "by_method": {},
    "by_path": {},
    "by_status": {},
    "bytes_sent": 0,
    "by_path_status": {},
}
WEB_VISITORS = {}
WEB_PATH_LAST_SEEN = {}
IP_EVENTS = defaultdict(deque)
THREAT_HISTORY = {}
WEB_STATS_STORAGE_PATH = Path(environ.get("WEB_STATS_STORAGE_PATH", str(ROOT / ".web-stats.json")))
WEB_STATS_PERSIST_INTERVAL_SECONDS = 2
WEB_STATS_PERSIST_LOCK = threading.Lock()
LAST_WEB_STATS_PERSIST_AT = 0.0
IP_THREAT_WINDOW_SECONDS = 300
IP_EVENT_MAX = 120
WEB_404_RETENTION_SECONDS = 3600
GEOIP_READER = None
GEOIP_LEGACY_READER = None
GEOIP_CACHE = {}
GEOIP_DIAGNOSTICS = {
    "last_mode": "not tested",
    "last_path": "",
    "last_error": "",
    "lookups": 0,
    "failures": 0,
}




def _stats_payload_locked():
    return {
        "version": 1,
        "web_stats": copy.deepcopy(WEB_STATS),
        "web_visitors": copy.deepcopy(WEB_VISITORS),
        "web_path_last_seen": [
            {"path": path, "status": status, "last_seen": timestamp}
            for (path, status), timestamp in WEB_PATH_LAST_SEEN.items()
        ],
        "threat_history": [
            {"ip": ip, "reason": reason, **copy.deepcopy(item)}
            for (ip, reason), item in THREAT_HISTORY.items()
        ],
    }


def persist_web_stats(force=False):
    """Persist dashboard counters atomically without blocking every request on disk I/O."""
    global LAST_WEB_STATS_PERSIST_AT
    with WEB_STATS_PERSIST_LOCK:
        now = time.time()
        if not force and now - LAST_WEB_STATS_PERSIST_AT < WEB_STATS_PERSIST_INTERVAL_SECONDS:
            return
        with WEB_STATS_LOCK:
            payload = _stats_payload_locked()
        temporary_path = WEB_STATS_STORAGE_PATH.with_name(f"{WEB_STATS_STORAGE_PATH.name}.tmp")
        try:
            WEB_STATS_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with temporary_path.open("w", encoding="utf-8") as temporary:
                json.dump(payload, temporary, ensure_ascii=False, separators=(",", ":"))
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, WEB_STATS_STORAGE_PATH)
            LAST_WEB_STATS_PERSIST_AT = now
        except OSError:
            temporary_path.unlink(missing_ok=True)
            LOGGER.exception("Impossible de persister les statistiques web: %s", WEB_STATS_STORAGE_PATH)


def load_persisted_web_stats():
    """Restore dashboard counters and threat history after a process restart."""
    if not WEB_STATS_STORAGE_PATH.is_file():
        LOGGER.info("Aucun historique web persistant: initialisation de %s", WEB_STATS_STORAGE_PATH)
        persist_web_stats(force=True)
        return
    try:
        payload = json.loads(WEB_STATS_STORAGE_PATH.read_text(encoding="utf-8"))
        with WEB_STATS_LOCK:
            stored_web = payload.get("web_stats", {})
            for key in ("by_method", "by_path", "by_status", "by_path_status"):
                if isinstance(stored_web.get(key), dict):
                    WEB_STATS[key].update(stored_web[key])
            for key in ("total_requests", "bytes_sent"):
                if isinstance(stored_web.get(key), int):
                    WEB_STATS[key] = stored_web[key]
            if isinstance(payload.get("web_visitors"), dict):
                WEB_VISITORS.update(payload["web_visitors"])
            for item in payload.get("web_path_last_seen", []):
                path, status, timestamp = item.get("path"), item.get("status"), item.get("last_seen")
                if isinstance(path, str) and isinstance(status, str) and isinstance(timestamp, (int, float)):
                    WEB_PATH_LAST_SEEN[(path, status)] = timestamp
            for item in payload.get("threat_history", []):
                ip, reason = item.get("ip"), item.get("reason")
                if not isinstance(ip, str) or not isinstance(reason, str):
                    continue
                entry = {key: value for key, value in item.items() if key not in {"ip", "reason"}}
                entry["ip"] = ip
                entry["reason"] = reason
                entry.setdefault("requests", 0)
                entry.setdefault("errors", 0)
                entry.setdefault("status_counts", {})
                entry.setdefault("paths", [])
                entry.setdefault("first_seen_epoch", time.time())
                entry.setdefault("last_seen_epoch", entry["first_seen_epoch"])
                THREAT_HISTORY[(ip, reason)] = entry
        LOGGER.info(
            "Historique web restauré: fichier=%s menaces=%s visiteurs=%s requêtes=%s",
            WEB_STATS_STORAGE_PATH,
            len(THREAT_HISTORY),
            len(WEB_VISITORS),
            WEB_STATS["total_requests"],
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        LOGGER.exception("Impossible de charger l'historique web persistant: %s", WEB_STATS_STORAGE_PATH)


def reset_persisted_web_stats():
    """Clear in-memory and persisted dashboard history."""
    with WEB_STATS_LOCK:
        WEB_STATS.update({
            "total_requests": 0,
            "by_method": {},
            "by_path": {},
            "by_status": {},
            "bytes_sent": 0,
            "by_path_status": {},
        })
        WEB_VISITORS.clear()
        WEB_PATH_LAST_SEEN.clear()
        IP_EVENTS.clear()
        THREAT_HISTORY.clear()
    persist_web_stats(force=True)


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
    return len(objects), width, height


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


def decode_photos(value):
    values = value if isinstance(value, list) else ([value] if value else [])
    if len(values) > 3:
        raise ValueError("Trois photos maximum par demande")
    photos = []
    for item in values:
        photo = decode_photo(item)
        if photo:
            photos.append(photo)
    return photos


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


def serialize_pdf_objects(objects):
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


def make_pdf(data, document_url):
    """Build a branded A4 PDF with customer block, request, photo and QR code."""
    orange = (0.93, 0.42, 0.23)
    ink = (0.09, 0.13, 0.12)
    muted = (0.34, 0.38, 0.36)

    def fill(color):
        return f"{color[0]} {color[1]} {color[2]} rg"

    def lower_semicircle(cx, cy, radius):
        k = radius * 0.5522848
        return (
            f"{cx - radius:g} {cy:g} m "
            f"{cx - radius:g} {cy - k:g} {cx - k:g} {cy - radius:g} {cx:g} {cy - radius:g} c "
            f"{cx + k:g} {cy - radius:g} {cx + radius:g} {cy - k:g} {cx + radius:g} {cy:g} c h"
        )

    def circle(cx, cy, radius):
        k = radius * 0.5522848
        return (
            f"{cx + radius:g} {cy:g} m "
            f"{cx + radius:g} {cy + k:g} {cx + k:g} {cy + radius:g} {cx:g} {cy + radius:g} c "
            f"{cx - k:g} {cy + radius:g} {cx - radius:g} {cy + k:g} {cx - radius:g} {cy:g} c "
            f"{cx - radius:g} {cy - k:g} {cx - k:g} {cy - radius:g} {cx:g} {cy - radius:g} c "
            f"{cx + k:g} {cy - radius:g} {cx + radius:g} {cy - k:g} {cx + radius:g} {cy:g} c h"
        )

    commands = [
        "q",
        fill(orange), "55 835 495 3 re f",
        # Two recognizable truck-tire halves hang from the orange roof line.
        fill(ink),
        lower_semicircle(330, 835, 20) + " f",
        lower_semicircle(415, 835, 20) + " f",
        "0.67 0.69 0.68 rg",
        lower_semicircle(330, 835, 13) + " f",
        lower_semicircle(415, 835, 13) + " f",
        "0.09 0.13 0.12 rg",
        lower_semicircle(330, 835, 7) + " f",
        lower_semicircle(415, 835, 7) + " f",
        "0.82 0.83 0.80 rg",
        circle(323, 829, 1.5) + " f", circle(330, 826, 1.5) + " f", circle(337, 829, 1.5) + " f",
        circle(408, 829, 1.5) + " f", circle(415, 826, 1.5) + " f", circle(422, 829, 1.5) + " f",
        "BT", "/F1 24 Tf", fill(ink), "55 810 Td", pdf_text(LEGAL_BUSINESS_NAME.upper()), "ET",
        "BT", "/F1 10 Tf", fill(orange), "55 790 Td", pdf_text("Réparer plutôt que remplacer"), "ET",
        "BT", "/F1 10 Tf", fill(ink), "460 815 Td", pdf_text(LEGAL_CONTACT_NAME or LEGAL_BUSINESS_NAME), "ET",
        "BT", "/F1 8 Tf", fill(orange), "460 800 Td", pdf_text(LEGAL_PHONE), "ET",
        "BT", "/F1 8 Tf", fill(orange), "460 785 Td", pdf_text(LEGAL_EMAIL), "ET",
        "Q",
    ]

    # Customer cartouche, moved directly below the header.
    commands += [
        "BT", "/F1 13 Tf", fill(ink), "62 722 Td", pdf_text(f"{data['firstname']} {data['lastname']}"), "ET",
        "BT", "/F1 9 Tf", fill(ink), "62 705 Td", pdf_text(data["phone"]), "ET",
        "BT", "/F1 9 Tf", fill(muted), "285 722 Td", pdf_text(data.get("location") or "Lieu non précisé"), "ET",
        "BT", "/F1 9 Tf", fill(muted), "285 705 Td", pdf_text(data.get("access") or "Accès non précisé"), "ET",
    ]

    # Request cartouche, with text reduced by approximately 40%.
    commands += [
    ]

    def append_request_field(x, y, label, value, width):
        commands.extend(["BT", "/F1 6 Tf", fill(orange), f"{x} {y} Td", pdf_text(label.upper()), "ET"])
        y -= 10
        lines = wrap_lines(value, width)
        commands.extend(["BT", "/F1 7 Tf", fill(ink), f"{x} {y} Td", pdf_text(lines[0]), "ET"])
        y -= 11
        for line in lines[1:3]:
            commands.extend(["BT", "/F1 7 Tf", fill(ink), f"{x + 8} {y} Td", pdf_text(line), "ET"])
            y -= 10
        return y - 4

    append_request_field(62, 655, "DATE", data.get("created_at", "Date non précisée"), 55)
    left_y = 625
    left_y = append_request_field(62, left_y, "Besoin", data.get("service"), 38)
    left_y = append_request_field(62, left_y, "Objet ou équipement", data.get("object"), 38)
    append_request_field(62, left_y, "Description", data.get("description"), 38)

    right_y = 625
    right_y = append_request_field(285, right_y, "Disponibilité", data.get("availability"), 28)
    append_request_field(285, right_y, "Urgence", data.get("urgency"), 28)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    image_refs = {}
    qr_ref, qr_width, qr_height = add_rgb_image(objects, qr_png(document_url), "QR")
    image_refs["QR"] = qr_ref

    photo_bytes_list = decode_photos(data.get("photo_data"))
    photo_dimensions = []
    for index, photo_bytes in enumerate(photo_bytes_list, start=1):
        photo_ref, photo_width, photo_height = add_rgb_image(objects, photo_bytes, f"PHOTO_{index}")
        image_refs[f"PHOTO_{index}"] = photo_ref
        photo_dimensions.append((photo_width, photo_height))

    # Follow-up cartouche directly after the request.
    commands += [
        "BT", "/F1 6 Tf", fill(orange), "62 517 Td", pdf_text("STATUT"), "ET",
        "BT", "/F1 7 Tf", fill(ink), "62 506 Td", pdf_text("A traiter"), "ET",
        "BT", "/F1 6 Tf", fill(orange), "285 517 Td", pdf_text("OBSERVATION"), "ET",
        "BT", "/F1 7 Tf", fill(muted), "285 506 Td", pdf_text("Aucune observation"), "ET",
    ]

    # Only render the photo block when a photo was actually supplied.
    if photo_dimensions:
        commands += [
            "BT", "/F1 6 Tf", fill(orange), "55 265 Td", pdf_text("PHOTOS JOINTES"), "ET",
        ]
        max_width, max_height, gap = 475, 90, 8
        tile_width = (max_width - gap * (len(photo_dimensions) - 1)) / len(photo_dimensions)
        for index, (photo_width, photo_height) in enumerate(photo_dimensions, start=1):
            photo_scale = min(tile_width / photo_width, max_height / photo_height)
            drawn_width = photo_width * photo_scale
            drawn_height = photo_height * photo_scale
            photo_x = 55 + (index - 1) * (tile_width + gap) + (tile_width - drawn_width) / 2
            photo_y = 65 + (max_height - drawn_height) / 2
            commands += [
                "q", f"{drawn_width:.3f} 0 0 {drawn_height:.3f} {photo_x:.3f} {photo_y:.3f} cm", f"/PHOTO_{index} Do", "Q",
            ]

    qr_size = 37.5
    qr_x, qr_y = 500, 20
    commands += [
        "q", f"{qr_size:g} 0 0 {qr_size:g} {qr_x:g} {qr_y:g} cm", "/QR Do", "Q",
    ]
    legal_text = " - ".join(
        value for value in (
            LEGAL_BUSINESS_NAME,
            LEGAL_CONTACT_NAME,
            LEGAL_PHONE,
            LEGAL_REGISTRATION,
            LEGAL_EMAIL,
        ) if value
    )
    legal_x = (595 - len(legal_text) * 7 * 0.48) / 2
    commands += [
        "BT", "/F1 9 Tf", fill(muted), "55 36 Td", pdf_text(f"Référence : {data['request_id']}"), "ET",
        "BT", "/F1 7 Tf", fill(muted), f"{legal_x:.1f} 18 Td", pdf_text(legal_text), "ET",
    ]
    content = "\n".join(commands).encode("ascii")

    xobjects = " /XObject << " + " ".join(f"/{name} {ref} 0 R" for name, ref in image_refs.items()) + " >>"
    objects[3] = (
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream"
    )
    escaped_url = document_url.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    annotation_ref = len(objects) + 1
    objects.append(
        f"<< /Type /Annot /Subtype /Link /Rect [500 20 537.5 57.5] /Border [0 0 0] "
        f"/A << /S /URI /URI ({escaped_url}) >> >>".encode("ascii")
    )
    objects[2] = (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        f"/Resources << /Font << /F1 5 0 R >>{xobjects} >> /Contents 4 0 R "
        f"/Annots [{annotation_ref} 0 R] >>"
    ).encode("ascii")

    return serialize_pdf_objects(objects)


def make_management_page(reference, history):
    """Build a transparent overlay that keeps request follow-up on page one."""
    orange = (0.93, 0.42, 0.23)
    ink = (0.09, 0.13, 0.12)
    muted = (0.34, 0.38, 0.36)

    def fill(color):
        return f"{color[0]} {color[1]} {color[2]} rg"

    current = history[-1]
    entries = history[-5:]
    commands = [
        "1 1 1 rg", "45 415 505 145 re f",
        "BT", "/F1 6 Tf", fill(orange), "62 517 Td", pdf_text("STATUT"), "ET",
        "BT", "/F1 7 Tf", fill(ink), "62 506 Td", pdf_text(current["status"]), "ET",
        "BT", "/F1 6 Tf", fill(orange), "285 517 Td", pdf_text("HISTORIQUE"), "ET",
    ]
    if len(history) > len(entries):
        commands.extend(["BT", "/F1 6 Tf", fill(muted), "285 506 Td", pdf_text(f"{len(history) - len(entries)} entrée(s) antérieure(s) non affichée(s)"), "ET"])
    y = 489
    for entry in entries:
        line = f"{entry['date']} — {entry['status']} — {entry['observation']}"
        commands.extend(["BT", "/F1 6 Tf", fill(muted), f"62 {y} Td", pdf_text(wrap_lines(line, 112)[0][:150]), "ET"])
        y -= 10
        if y < 214:
            break
    content = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    return serialize_pdf_objects(objects)


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
        f"Date et heure : {data['created_at']}\n"
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


def _pdf_text(pdf_path):
    if not shutil.which("pdftotext"):
        LOGGER.error("Extraction PDF impossible: pdftotext introuvable")
        return ""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        LOGGER.warning(
            "pdftotext a échoué pour %s (code=%s): %s",
            pdf_path.name,
            result.returncode,
            (result.stderr or "").strip()[:500],
        )
        return ""
    LOGGER.debug(
        "PDF extrait: fichier=%s caractères=%s lignes=%s",
        pdf_path.name,
        len(result.stdout),
        len(result.stdout.splitlines()),
    )
    return result.stdout


def _pdf_status(text):
    lines = [line.strip() for line in text.splitlines()]
    matches = []
    for index, line in enumerate(lines):
        if line in ("STATUT", "STATUT :"):
            for candidate in lines[index + 1:]:
                if candidate:
                    matches.append(candidate)
                    break
    if matches and matches[-1] in REQUEST_STATUSES:
        return matches[-1]
    history = _pdf_management_history(text)
    return history[-1]["status"] if history else "A traiter"


def _pdf_management_history(text):
    history = []
    for page in text.split("\f"):
        if "SUIVI DE LA DEMANDE" in page:
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            try:
                status_index = lines.index("STATUT")
                date_index = lines.index("DATE DU JOURNAL")
                observation_index = lines.index("OBSERVATION")
                status = lines[status_index + 1]
                date = lines[date_index + 1]
                observation = " ".join(lines[observation_index + 1:])
                if status in REQUEST_STATUSES:
                    history.append({"status": status, "date": date, "observation": observation or "Aucune observation"})
            except (ValueError, IndexError):
                continue
        else:
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            for line in lines:
                match = re.match(r"^(\d{2}/\d{2}/\d{4} à \d{2}:\d{2})\s+—\s+(.+?)\s+—\s+(.*)$", line)
                if match and match.group(2) in REQUEST_STATUSES:
                    history.append({"date": match.group(1), "status": match.group(2), "observation": match.group(3)})
    return history


def append_management_page(pdf_path, reference, status, observation):
    if not shutil.which("qpdf"):
        raise RuntimeError("Le programme qpdf est requis pour journaliser le suivi sur la page PDF")
    management_fd, management_name = tempfile.mkstemp(prefix=f".{reference}-", suffix="-status.pdf", dir=REQUEST_STORAGE_DIR)
    base_fd, base_name = tempfile.mkstemp(prefix=f".{reference}-", suffix="-base.pdf", dir=REQUEST_STORAGE_DIR)
    output_fd, output_name = tempfile.mkstemp(prefix=f".{reference}-", suffix="-updated.pdf", dir=REQUEST_STORAGE_DIR)
    os.close(management_fd)
    os.close(base_fd)
    os.close(output_fd)
    try:
        history = _pdf_management_history(_pdf_text(pdf_path))
        history.append({
            "status": status,
            "date": datetime.now().astimezone().strftime("%d/%m/%Y à %H:%M"),
            "observation": observation or "Aucune observation",
        })
        Path(management_name).write_bytes(make_management_page(reference, history))
        subprocess.run(
            ["qpdf", str(pdf_path), "--pages", ".", "1", "--", base_name],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        subprocess.run(
            ["qpdf", "--overlay", management_name, "--", base_name, output_name],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        os.replace(output_name, pdf_path)
    finally:
        for temporary_path in (management_name, base_name, output_name):
            try:
                Path(temporary_path).unlink()
            except FileNotFoundError:
                pass


def _pdf_field(lines, label):
    labels = (
        "DATE TIMESTAMP", "DATE", "BESOIN", "OBJET OU ÉQUIPEMENT", "DESCRIPTION",
        "DISPONIBILITÉ", "URGENCE", "PHOTO JOINTE", "DOCUMENT EN LIGNE", "Référence",
    )
    for index, line in enumerate(lines):
        position = line.find(label)
        if position < 0:
            continue
        next_positions = [line.find(candidate, position + len(label)) for candidate in labels]
        next_positions = [candidate for candidate in next_positions if candidate >= 0]
        end = min(next_positions) if next_positions else len(line)
        inline = line[position + len(label):end].strip()
        if inline:
            return inline
        if index + 1 < len(lines):
            value_line = lines[index + 1]
            if next_positions:
                return value_line[position:end].strip()
            if position > 0:
                return value_line[position:].strip()
            return value_line.strip()
    return ""


def _pdf_location_parts(lines):
    try:
        request_index = lines.index("Votre demande")
        header_lines = lines[:request_index]
    except ValueError:
        header_lines = lines
    candidates = [line for line in header_lines if "," in line or re.search(r"\b\d{5}\b", line)]
    if candidates:
        location_line = candidates[-1]
        parts = [part.strip() for part in location_line.split(",") if part.strip()]
        if len(parts) >= 3:
            return parts[-2], parts[-1]
        if len(parts) == 2:
            return "", parts[-1]
        match = re.search(r"\b(\d{5})\b(?:\s+)([^,]+)$", location_line)
        if match:
            return match.group(1), match.group(2).strip()
    return "", ""


def _is_sensitive_probe(path):
    lowered = path.lower()
    return lowered.startswith((
        "/.git", "/.env", "/app.py", "/wp-admin", "/wp-login", "/xmlrpc.php",
        "/phpmyadmin", "/server-status", "/config", "/backup", "/data/",
    ))


def _threat_reason(events, now):
    client_errors = [event for event in events if 400 <= event[1] < 500]
    recent_errors = [event for event in client_errors if event[0] >= now - 60]
    sensitive_count = sum(1 for event in events if _is_sensitive_probe(event[2]))
    distinct_error_paths = {event[2] for event in recent_errors}
    consecutive_errors = 0
    for event in reversed(events):
        if 400 <= event[1] < 500:
            consecutive_errors += 1
        else:
            break
    if sensitive_count >= 2:
        return "Sonde de chemins sensibles"
    if consecutive_errors >= 3 and len(distinct_error_paths) >= 2:
        return "Erreurs 4xx consécutives sur plusieurs chemins"
    if len(recent_errors) >= 8 and len(distinct_error_paths) >= 4:
        return "Nombre élevé d’erreurs 4xx en une minute"
    return ""


def _record_ip_event(ip, status, path):
    """Track bounded request history and return a current threat reason, if any."""
    now = time.time()
    events = IP_EVENTS[ip]
    cutoff = now - IP_THREAT_WINDOW_SECONDS
    while events and events[0][0] < cutoff:
        events.popleft()
    events.append((now, status, path))
    while len(events) > IP_EVENT_MAX:
        events.popleft()
    return _threat_reason(events, now)


def _geoip(ip):
    """Return optional country/city data without making a network lookup."""
    cached = GEOIP_CACHE.get(ip)
    if cached is not None:
        return cached
    result = {"country": "—", "city": "—"}
    GEOIP_DIAGNOSTICS["lookups"] += 1
    try:
        global GEOIP_READER, GEOIP_LEGACY_READER
        if Path(GEOIP_DB_PATH).is_file():
            GEOIP_DIAGNOSTICS.update(last_mode="GeoIP2 mmdb", last_path=GEOIP_DB_PATH, last_error="")
            if GEOIP_READER is None:
                LOGGER.info("GeoIP: utilisation de la base GeoIP2 %s", GEOIP_DB_PATH)
                geoip_database = importlib.import_module("geoip2.database")
                GEOIP_READER = geoip_database.Reader(GEOIP_DB_PATH)
            response = GEOIP_READER.city(ip)
            result = {
                "country": response.country.name or response.country.iso_code or "—",
                "city": response.city.name or "—",
            }
        else:
            legacy_paths = [
                GEOIP_LEGACY_DB_PATH,
                "/opt/GeoIPv2/GeoLiteCity.dat",
                "/opt/GeoIPv1/GeoLiteCity.dat",
                "/usr/share/GeoIP/GeoLiteCity.dat",
            ]
            legacy_path = next((path for path in legacy_paths if path and Path(path).is_file()), "")
            if legacy_path:
                GEOIP_DIAGNOSTICS.update(last_mode="GeoIP legacy dat", last_path=legacy_path, last_error="")
                if GEOIP_LEGACY_READER is None:
                    LOGGER.info("GeoIP: utilisation de la base legacy %s", legacy_path)
                    legacy_database = importlib.import_module("GeoIP")
                    GEOIP_LEGACY_READER = legacy_database.open(legacy_path, legacy_database.GEOIP_STANDARD)
                record = GEOIP_LEGACY_READER.record_by_addr(ip) or {}
                result = {
                    "country": record.get("country_name") or record.get("country_code") or "—",
                    "city": record.get("city") or "—",
                }
            else:
                GEOIP_DIAGNOSTICS.update(last_mode="no database", last_path="", last_error="Aucune base GeoIP trouvée")
                LOGGER.warning(
                    "GeoIP indisponible: aucune base trouvée (mmdb=%s, legacy=%s)",
                    GEOIP_DB_PATH,
                    GEOIP_LEGACY_DB_PATH or "non configurée",
                )
    except (ImportError, OSError, ValueError):
        GEOIP_DIAGNOSTICS["failures"] += 1
        GEOIP_DIAGNOSTICS["last_error"] = "Bibliothèque absente, base illisible ou adresse invalide"
        LOGGER.exception("GeoIP échec pour %s", ip)
    except Exception as error:
        GEOIP_DIAGNOSTICS["failures"] += 1
        GEOIP_DIAGNOSTICS["last_error"] = str(error)
        LOGGER.exception("GeoIP erreur inattendue pour %s", ip)
    GEOIP_CACHE[ip] = result
    return result


def geoip_diagnostics():
    candidates = [GEOIP_DB_PATH, GEOIP_LEGACY_DB_PATH, "/opt/GeoIPv2/GeoLiteCity.dat", "/opt/GeoIPv1/GeoLiteCity.dat"]
    return {
        **GEOIP_DIAGNOSTICS,
        "configured_mmdb": GEOIP_DB_PATH,
        "configured_legacy": GEOIP_LEGACY_DB_PATH or "",
        "candidates": [
            {"path": path, "exists": Path(path).is_file(), "readable": os.access(path, os.R_OK)}
            for path in dict.fromkeys(path for path in candidates if path)
        ],
        "cache_entries": len(GEOIP_CACHE),
        "geoip2_reader_loaded": GEOIP_READER is not None,
        "legacy_reader_loaded": GEOIP_LEGACY_READER is not None,
    }


def collect_threats():
    with WEB_STATS_LOCK:
        snapshots = list(THREAT_HISTORY.values())
    threats = []
    for item in snapshots:
        geo = _geoip(item["ip"])
        threats.append({
            **item,
            "country": geo["country"],
            "city": geo["city"],
            "first_seen": datetime.fromtimestamp(item["first_seen_epoch"]).astimezone().isoformat(timespec="seconds"),
            "last_seen": datetime.fromtimestamp(item["last_seen_epoch"]).astimezone().isoformat(timespec="seconds"),
        })
    return sorted(threats, key=lambda item: item["last_seen"], reverse=True)


def record_threat_history(ip, reason, status, path):
    now = time.time()
    key = (ip, reason)
    item = THREAT_HISTORY.setdefault(key, {
        "ip": ip,
        "reason": reason,
        "requests": 0,
        "errors": 0,
        "status_counts": {},
        "paths": [],
        "first_seen_epoch": now,
        "last_seen_epoch": now,
    })
    item["requests"] += 1
    item["errors"] += int(400 <= status < 500)
    item["status_counts"][str(status)] = item["status_counts"].get(str(status), 0) + 1
    item["paths"] = list(dict.fromkeys([*item["paths"], path]))[-8:]
    item["last_seen_epoch"] = now
    while len(THREAT_HISTORY) > 2048:
        oldest_key = min(THREAT_HISTORY, key=lambda candidate: THREAT_HISTORY[candidate]["last_seen_epoch"])
        THREAT_HISTORY.pop(oldest_key, None)


def collect_admin_stats():
    """Return process web counters and metadata extracted from stored request PDFs."""
    request_rows = []
    scan_errors = 0
    LOGGER.info(
        "Scan PDF admin: dossier=%s existe=%s lisible=%s",
        REQUEST_STORAGE_DIR,
        REQUEST_STORAGE_DIR.is_dir(),
        os.access(REQUEST_STORAGE_DIR, os.R_OK) if REQUEST_STORAGE_DIR.exists() else False,
    )
    if REQUEST_STORAGE_DIR.is_dir():
        pdf_paths = sorted(
            path for path in REQUEST_STORAGE_DIR.glob("*.pdf")
            if REQUEST_REFERENCE_RE.fullmatch(path.stem)
        )
    else:
        pdf_paths = []
    LOGGER.info("Scan PDF admin: %s fichier(s) correspondant au motif", len(pdf_paths))
    for pdf_path in pdf_paths:
        try:
            text = _pdf_text(pdf_path)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            modified_at = datetime.fromtimestamp(pdf_path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            postcode, town = _pdf_location_parts(lines)
            service = _pdf_field(lines, "BESOIN")
            availability = _pdf_field(lines, "DISPONIBILITÉ")
            urgency = _pdf_field(lines, "URGENCE")
            request_status = _pdf_status(text)
            LOGGER.info(
                "PDF analysé: fichier=%s caractères=%s lignes=%s besoin=%s disponibilité=%s urgence=%s code_postal=%s commune=%s",
                pdf_path.name,
                len(text),
                len(lines),
                bool(service),
                bool(availability),
                bool(urgency),
                bool(postcode),
                bool(town),
            )
            request_rows.append({
                "reference": pdf_path.stem,
                "date": _pdf_field(lines, "DATE") or _pdf_field(lines, "DATE TIMESTAMP") or modified_at,
                "service": service,
                "availability": availability,
                "urgency": urgency,
                "status": request_status,
                "postcode": postcode,
                "town": town,
                "size_bytes": pdf_path.stat().st_size,
                "modified_at": modified_at,
            })
        except (OSError, subprocess.SubprocessError, ValueError):
            scan_errors += 1
            LOGGER.exception("Erreur pendant l'analyse du PDF %s", pdf_path.name)

    with WEB_STATS_LOCK:
        now = time.time()
        visible_path_status = {}
        for path, statuses in WEB_STATS["by_path_status"].items():
            visible_statuses = {
                status: count
                for status, count in statuses.items()
                if status != "404"
                or now - WEB_PATH_LAST_SEEN.get((path, status), now) < WEB_404_RETENTION_SECONDS
            }
            if visible_statuses:
                visible_path_status[path] = visible_statuses
        web = {
            "total_requests": WEB_STATS["total_requests"],
            "by_method": dict(WEB_STATS["by_method"]),
            "by_path": dict(WEB_STATS["by_path"]),
            "by_status": dict(WEB_STATS["by_status"]),
            "bytes_sent": WEB_STATS["bytes_sent"],
            "by_path_status": {
                path: dict(statuses)
                for path, statuses in visible_path_status.items()
            },
            "visitors": [
                {
                    "ip": ip,
                    "requests": details["requests"],
                    "bytes_sent": details["bytes_sent"],
                    "last_seen": datetime.fromtimestamp(details["last_seen"]).astimezone().isoformat(timespec="seconds"),
                    **_geoip(ip),
                }
                for ip, details in sorted(
                    WEB_VISITORS.items(),
                    key=lambda item: item[1]["last_seen"],
                    reverse=True,
                )[:200]
            ],
            "geoip": geoip_diagnostics(),
        }
    def count_by(field):
        values = {}
        for row in request_rows:
            value = row[field] or "Non précisé"
            values[value] = values.get(value, 0) + 1
        return dict(sorted(values.items(), key=lambda item: (-item[1], item[0])))

    return {
        "commit": APP_COMMIT,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "server_started_at": datetime.fromtimestamp(SERVER_STARTED_AT).astimezone().isoformat(timespec="seconds"),
        "uptime_seconds": round(time.time() - SERVER_STARTED_AT),
        "web": web,
        "threats": collect_threats(),
        "requests": {
            "count": len(request_rows),
            "total_bytes": sum(row["size_bytes"] for row in request_rows),
            "scan_errors": scan_errors,
            "by_service": count_by("service"),
            "by_availability": count_by("availability"),
            "by_urgency": count_by("urgency"),
            "by_status": count_by("status"),
            "items": list(reversed(request_rows[-200:])),
        },
    }


class SiteHandler(SimpleHTTPRequestHandler):
    """Sert les fichiers statiques et les demandes PDF."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def client_ip(self):
        """Return the public client IP forwarded by the trusted local proxy."""
        peer_ip = self.client_address[0]
        if peer_ip in {"127.0.0.1", "::1"}:
            forwarded = self.headers.get("X-Forwarded-For", "")
            candidate = forwarded.split(",", 1)[0].strip() if forwarded else self.headers.get("X-Real-IP", "").strip()
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                pass
        return peer_ip

    def address_string(self):
        return self.client_ip()

    def log_request(self, code="-", size="-"):
        path = urlparse(self.path).path[:160]
        status = str(code)
        status_code = int(status) if status.isdigit() else 0
        sent = int(size) if str(size).isdigit() else 0
        client_ip = self.client_ip()
        with WEB_STATS_LOCK:
            WEB_STATS["total_requests"] += 1
            WEB_STATS["bytes_sent"] += sent
            WEB_STATS["by_method"][self.command] = WEB_STATS["by_method"].get(self.command, 0) + 1
            WEB_STATS["by_path"][path] = WEB_STATS["by_path"].get(path, 0) + 1
            WEB_STATS["by_status"][status] = WEB_STATS["by_status"].get(status, 0) + 1
            path_statuses = WEB_STATS["by_path_status"].setdefault(path, {})
            path_statuses[status] = path_statuses.get(status, 0) + 1
            WEB_PATH_LAST_SEEN[(path, status)] = time.time()
            visitor = WEB_VISITORS.setdefault(client_ip, {"requests": 0, "bytes_sent": 0, "last_seen": 0})
            visitor["requests"] += 1
            visitor["bytes_sent"] += sent
            visitor["last_seen"] = time.time()
            if len(WEB_VISITORS) > 2048:
                oldest_visitor = min(WEB_VISITORS, key=lambda ip: WEB_VISITORS[ip]["last_seen"])
                WEB_VISITORS.pop(oldest_visitor, None)
            threat_reason = _record_ip_event(client_ip, status_code, path)
            if len(IP_EVENTS) > 2048:
                oldest_ip = min(IP_EVENTS, key=lambda ip: IP_EVENTS[ip][-1][0] if IP_EVENTS[ip] else 0)
                IP_EVENTS.pop(oldest_ip, None)
        threat_detected = bool(threat_reason and (status_code >= 400 or _is_sensitive_probe(path)))
        if threat_detected:
            with WEB_STATS_LOCK:
                record_threat_history(client_ip, threat_reason, status_code, path)
            LOGGER.warning(
                "Menace potentielle: ip=%s raison=%s chemin=%s statut=%s",
                client_ip,
                threat_reason,
                path,
                status,
            )
        persist_web_stats(force=threat_detected)
        super().log_request(code, size)

    def _require_admin(self):
        if not ADMIN_PASSWORD:
            self.send_error(404)
            return False
        authorization = self.headers.get("Authorization", "")
        expected = base64.b64encode(f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode()).decode()
        if not hmac.compare_digest(authorization, f"Basic {expected}"):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="L\'Atelier Roulant administration"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/admin", "/admin/", "/admin.html"}:
            if not self._require_admin():
                return
            self.path = "/admin.html"
            super().do_GET()
            return
        if path == "/api/admin/stats":
            if not self._require_admin():
                return
            self.respond_json(200, collect_admin_stats())
            return
        if path == "/api/public-config":
            self.respond_json(200, {
                "legal": {
                    "business_name": LEGAL_BUSINESS_NAME,
                    "contact_name": LEGAL_CONTACT_NAME,
                    "phone": LEGAL_PHONE,
                    "registration": LEGAL_REGISTRATION,
                    "email": LEGAL_EMAIL,
                },
            })
            return
        match = re.fullmatch(r"/requests/((?:[A-F0-9]{12}|[A-F0-9]{32}))\.pdf", path)
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
        path = urlparse(self.path).path
        if path == "/api/admin/reset-stats":
            if not self._require_admin():
                return
            if self.headers.get("X-Admin-Action") != "reset-stats":
                self.respond_json(403, {"ok": False, "error": "Action d’administration non autorisée"})
                return
            reset_persisted_web_stats()
            self.respond_json(200, {"ok": True})
            return
        if path == "/api/admin/update-request":
            if not self._require_admin():
                return
            if self.headers.get("X-Admin-Action") != "update-request":
                self.respond_json(403, {"ok": False, "error": "Action d’administration non autorisée"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 4_000:
                    raise ValueError("Requête trop volumineuse")
                payload = json.loads(self.rfile.read(length))
                reference = str(payload.get("reference", "")).upper()
                status = str(payload.get("status", "")).strip()
                observation = str(payload.get("observation", "")).strip()
                if not REQUEST_REFERENCE_RE.fullmatch(reference):
                    raise ValueError("Référence de demande invalide")
                if status not in REQUEST_STATUSES:
                    raise ValueError("Statut de demande invalide")
                if len(observation) > 2_000:
                    raise ValueError("Observation trop longue")
                pdf_path = REQUEST_STORAGE_DIR / f"{reference}.pdf"
                if not pdf_path.is_file():
                    self.respond_json(404, {"ok": False, "error": "PDF introuvable"})
                    return
                append_management_page(pdf_path, reference, status, observation or "Aucune observation")
                self.respond_json(200, {"ok": True, "reference": reference, "status": status})
            except (ValueError, json.JSONDecodeError) as error:
                self.respond_json(400, {"ok": False, "error": str(error)})
            except (OSError, subprocess.SubprocessError) as error:
                self.respond_json(503, {"ok": False, "error": str(error)})
            return
        if path == "/api/admin/delete-request":
            if not self._require_admin():
                return
            if self.headers.get("X-Admin-Action") != "delete-request":
                self.respond_json(403, {"ok": False, "error": "Action d’administration non autorisée"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 2_000:
                    raise ValueError("Requête trop volumineuse")
                payload = json.loads(self.rfile.read(length))
                reference = str(payload.get("reference", "")).upper()
                if not REQUEST_REFERENCE_RE.fullmatch(reference):
                    raise ValueError("Référence de demande invalide")
                pdf_path = REQUEST_STORAGE_DIR / f"{reference}.pdf"
                if not pdf_path.is_file():
                    self.respond_json(404, {"ok": False, "error": "PDF introuvable"})
                    return
                pdf_path.unlink()
                self.respond_json(200, {"ok": True, "reference": reference})
            except (ValueError, json.JSONDecodeError) as error:
                self.respond_json(400, {"ok": False, "error": str(error)})
            except OSError as error:
                self.respond_json(503, {"ok": False, "error": str(error)})
            return
        if path != "/api/submit-request":
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
            data["request_id"] = uuid.uuid4().hex.upper()
            data["created_at"] = datetime.now().astimezone().strftime("%d/%m/%Y à %H:%M")
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
    load_persisted_web_stats()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), SiteHandler)
    print(f"L’Atelier Roulant est disponible sur http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.server_close()
