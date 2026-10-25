# L'Atelier Roulant

Mobile repair and reuse service website. The application provides:

- Three.js welcome scene and mairie information scene;
- five-step service request wizard;
- up to three image uploads per request;
- one-page PDF generation with QR code and clickable PDF link;
- SMTP notification to the configured owner address;
- HTTP Basic Auth administration;
- persistent traffic, visitor, path, and threat statistics;
- PDF-based request status and observation history.

## Runtime

- Python 3
- Pillow
- `qrencode` — QR generation
- `qpdf` — PDF follow-up overlay
- `pdftotext` — admin PDF extraction
- `git` — runtime commit display; direct `.git` reading is used as fallback
- Optional GeoIP:
  - Python `geoip2` + GeoLite2 `.mmdb`, or
  - Python `GeoIP` + legacy `.dat`
- Browser JavaScript/WebGL
- Three.js is loaded from a CDN by `index.html`

Check the local runtime before starting:

```bash
python3 scripts/check_dependencies.py
```

The check reports missing binaries, Python modules, assets, writable storage, SMTP configuration, and URL configuration. `app.py` performs the same non-blocking checks at startup.

## Local development

```bash
python3 app.py
# http://127.0.0.1:8000
```

Change the port with:

```bash
PORT=8080 python3 app.py
```

The development server should be bound to loopback only. Do not expose it directly to the Internet.

## Configuration

Use environment variables or a protected systemd environment file. Never commit passwords, tokens, or private keys.

### Application

| Variable | Purpose | Default |
|---|---|---|
| `APP_HOME` | Logical application root | Directory containing `app.py` |
| `PORT` | HTTP listen port | `8000` |
| `PUBLIC_BASE_URL` | Public PDF and QR base URL | `https://atelier-roulant.linuxtribe.fr` |
| `REQUEST_STORAGE_DIR` | PDF storage directory | `requests/`, then `data/requests/` |
| `OWNER_EMAIL` | Notification recipient | `me@my.mail` |
| `WEB_STATS_STORAGE_PATH` | Persistent statistics file | `$APP_HOME/.web-stats.json` |

### SMTP

| Variable | Purpose |
|---|---|
| `SMTP_HOST` | SMTP server |
| `SMTP_PORT` | SMTP port; `587` by default |
| `SMTP_USERNAME` | SMTP login; defaults to `OWNER_EMAIL` |
| `SMTP_PASSWORD` | SMTP password; required for submission |
| `SMTP_FROM` | Sender address |
| `SMTP_STARTTLS` | Enable STARTTLS on the SMTP connection |
| `SMTP_SSL` | Use implicit TLS, e.g. port `465` |

Example, with the password supplied outside Git:

```bash
export OWNER_EMAIL='operator@example.invalid'
export SMTP_HOST='smtp.example.invalid'
export SMTP_PORT='587'
export SMTP_USERNAME='operator@example.invalid'
export SMTP_PASSWORD='[REDACTED]'
export SMTP_FROM='operator@example.invalid'
export SMTP_STARTTLS='1'
```

SMTP failures are returned to the browser. The application distinguishes PDF generation from notification delivery and does not claim delivery without an SMTP response.

### Legal data

These values are injected into the public footer and generated PDFs:

```bash
export LEGAL_BUSINESS_NAME='L\'Atelier Roulant'
export LEGAL_CONTACT_NAME='[NAME]'
export LEGAL_PHONE='[PHONE]'
export LEGAL_REGISTRATION='[REGISTRATION]'
export LEGAL_EMAIL='operator@example.invalid'
```

The public footer renders `LEGAL_PHONE` as a `tel:` link and `LEGAL_EMAIL` as a `mailto:` link.

### Administration and GeoIP

```bash
export ADMIN_USERNAME='admin'
export ADMIN_PASSWORD='[REDACTED]'
export GEOIP_DB_PATH='/usr/share/GeoIP/GeoLite2-City.mmdb'
export GEOIP_LEGACY_DB_PATH='/opt/GeoIPv2/GeoLiteCity.dat'
```

`/admin` and its JSON API require HTTP Basic Auth. If `ADMIN_PASSWORD` is unset, administration is disabled and returns `404`.

GeoIP is optional and uses local databases only. No remote GeoIP lookup is performed.

## Storage and PDFs

- Request PDFs are stored under `REQUEST_STORAGE_DIR`.
- New references use 32 uppercase hexadecimal characters.
- Legacy 12-character references remain readable.
- PDFs are served only by known opaque reference; storage directories are not listable through the application.
- Uploaded images are decoded with Pillow, converted to RGB, bounded, and placed with preserved aspect ratio.
- Empty photo lists produce no photo heading or placeholder.
- PDF photos are placed below the status/observation row and reserve space for the QR code and footer.
- Status and observation history is overlaid onto page one with `qpdf`; the PDF remains one page and no sidecar metadata file is used.
- The QR payload contains the complete public PDF URL and its PDF annotation uses the same rectangle.

The service account must be able to write to `REQUEST_STORAGE_DIR`. With systemd hardening enabled:

```ini
ReadWritePaths=/opt/latelier-roulant/requests
```

## HTTP surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Public site |
| `GET` | `/api/public-config` | Public legal configuration |
| `POST` | `/api/submit-request` | Validate request, create PDF, send notification |
| `GET` | `/requests/<REFERENCE>.pdf` | Retrieve a known PDF reference |
| `GET` | `/admin` | Authenticated administration |
| `GET` | `/api/admin/stats` | Authenticated dashboard data |
| `POST` | `/api/admin/update-request` | Authenticated PDF follow-up update |
| `POST` | `/api/admin/delete-request` | Authenticated PDF deletion |
| `POST` | `/api/admin/reset-stats` | Authenticated statistics reset |

The browser human-check is a UX gate, not a security boundary. `human_confirmed` must not be treated as a server-grade CAPTCHA token.

## Production checklist

1. Run `python3 scripts/check_dependencies.py` as the service user.
2. Configure SMTP, legal values, `PUBLIC_BASE_URL`, storage, and admin credentials outside Git.
3. Install the required binaries and Python modules.
4. Ensure `REQUEST_STORAGE_DIR` exists and is writable by the service user.
5. Bind Python to loopback and proxy it through Nginx.
6. Deny directory listing and source-file access in Nginx.
7. Run under a dedicated unprivileged systemd user.
8. Enable HTTPS and request-rate limiting at Nginx.
9. Restart the service after deployment and verify the reported commit in `/admin`.
10. Test one-photo, three-photo, no-photo, PDF follow-up, QR annotation, SMTP failure, and admin authorization paths.

## Repository layout

```text
app.py                       HTTP server, PDF generation, SMTP, admin API
index.html                   Public HTML and CSS
admin.html                   Admin dashboard
js/main.js                   Three.js scene and browser workflow
scripts/check_dependencies.py Runtime dependency checker
assets/                      Static assets
requests/ or data/requests/  Runtime PDF storage; do not commit
```
