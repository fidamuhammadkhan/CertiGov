# CertiGov v2 — Multi-Organization Certificate Platform

A working multi-tenant certificate issuance, A4 PDF creation, interactive template design and QR verification application for government, education and private organizations.

## Included (functional in this repository)

- Super-admin creation, organizations, suspension, subscription plans and payment-reference approval.
- Organization administrator, issuer, designer and read-only auditor roles; organization-scoped records.
- 500 algorithmically combined layouts **for each of 8 categories** (4,000 catalog variants total; 10 palettes × 10 layout variants × 5 frame treatments). They are configurable variants, **not** 4,000 hand-illustrated artworks.
- Drag-to-position editor; edit fields, colors, fonts, size, alignment; add text and lines; reuse QR, logo and signature placeholders.
- Upload JPG, PNG or PDF (first page) design background. Uploaded files are decoded and re-encoded as PNG, max 10 MB, max 20 MP.
- English/Pashto/Dari UI direction switching; RTL certificate generation using installed Noto Arabic fonts; three recipient-name fields and language-specific certificate titles.
- Issuance quotas and active subscription expiry, CSV batch issuing (max 100 per request), CSV report export (up to 20,000 records), PDF & QR generation, unique public tokens, public JSON and HTML verification, revocation, SHA-256 fingerprints and signed immutable metadata.
- Database audit log and role-scoped actions; session login, Argon2 hashing, CSRF protection, verification-rate limiting and HTTPS-ready container config.

## Free public HTTPS deployment with phone-scannable QR (Render + Neon)

The included `render.yaml` provides a free Docker web service configuration, and `STORAGE_BACKEND=database` keeps PDFs and uploads in a separate persistent Neon PostgreSQL database. Render supplies its own HTTPS URL automatically, which is embedded in newly issued certificates. Existing old-local-URL PDFs can be regenerated in the organization portal.

**Read `FREE_DEPLOYMENT_GUIDE.md` for exact setup steps in English, Pashto and Dari.** External account setup is required; this source archive is not itself a live hosted website. Free hosting can sleep or have quotas, so it is suitable for testing, not guaranteed government availability.

## Simplest start on a Windows laptop (Docker Desktop + WSL2)

1. Install Docker Desktop with the WSL2 backend, and start Docker Desktop.
2. Extract this ZIP into a normal folder. Copy `.env.example` to `.env`.
3. Replace `APP_SECRET` and `CERT_SIGNING_KEY` with two different random values (minimum 48 random bytes each). Example to generate one: `python -c "import secrets;print(secrets.token_urlsafe(48))"`.
4. From PowerShell, inside the extracted folder:

```powershell
docker compose -f docker-compose.dev.yml up --build -d
docker compose -f docker-compose.dev.yml exec app python manage.py create-admin
```

5. Open **http://127.0.0.1:8000** in a browser and sign in with the admin credentials you just created.

This demo starts locally with SQLite and full PDF fonts. QR links using `127.0.0.1` work **only on the same machine**. To use real phone QR scans, deploy to a reachable HTTPS hostname and set `PUBLIC_BASE_URL` before issuing documents.

## Fast local setup (Python 3.11+)

Open a terminal in the extracted directory. In Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:APP_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:CERT_SIGNING_KEY = (python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:PUBLIC_BASE_URL = 'http://127.0.0.1:8000'
python manage.py create-admin
python run.py
```

**Windows note:** WeasyPrint relies on Pango/GLib native libraries. The Python-only method may require additional Windows runtime libraries. The Docker method above is recommended, since its image installs these dependencies automatically.

Then open http://127.0.0.1:8000. On Linux/macOS use `python3 -m venv .venv`, `source .venv/bin/activate` and `export ...` instead of PowerShell syntax.

**For another phone to scan the QR code**, replace `PUBLIC_BASE_URL` with a public HTTPS hostname accessible to that phone, then issue **new** certificates. Certificates already issued retain their old embedded QR URL; use a permanent domain before live issuance.

### Try the complete process

1. Superadmin signs in, opens **Organizations**, creates e.g. Bakhtar University and its first organization administrator.
2. The organization administrator signs in, opens **Branding** to add official logo/signature and localized names.
3. Opens **Templates → Template Library**, chooses a category/design, drags the fields in the editor, uploads a background if wanted and saves.
4. Opens **Billing**, selects Starter/Professional/Enterprise and enters a bank-transfer reference.
5. Superadmin reviews the request in **Billing** and approves payment after *independently confirming* the transaction.
6. Organization issuer opens **Issue Certificate**, chooses a template, fills name in English/Pashto/Dari and selects language, then generates the certificate.
7. Download the A4 PDF. Scan its QR in a browser to verify original data, issue date, expiration and revocation status.
8. An organization admin can revoke a certificate; visiting the **same** QR afterwards shows its revoked status.
9. For groups, use **Bulk Import**, download the CSV sample and process up to 100 rows per request.

## Production Docker (PostgreSQL)

Copy `.env.example` to `.env`, replace all secrets with long random secrets, change `DATABASE_URL` or let Compose supply it, set `PUBLIC_BASE_URL=https://certificates.your-government-or-organization-domain.example`, add `POSTGRES_PASSWORD=<unique-strong-secret>` and set `PRODUCTION=true`.

```bash
docker compose up --build -d
docker compose exec app python manage.py create-admin
```

Compose binds app only to 127.0.0.1:8000. Place a managed HTTPS reverse proxy or ingress in front; configure trusted proxy headers, TLS termination and automatic certificate renewal. Do not expose ports directly to the public Internet without HTTPS. Back up both PostgreSQL and the `app_data` volume, and test restoring them.

### Deployment and security limitations (read before real government issuance)

This is a **functional full-stack starter, not a formally audited or accredited government trust service**. Before a real production launch, implement and validate:

- Independent security assessment, penetration testing, threat modeling, privacy notices and data-retention policy; legal review for official issuance and organization accreditation.
- Mandatory MFA / SSO for privileged accounts; password-reset and account-invitation flows; email service, notification queue; workflow approvals for high-assurance documents.
- Formal versioned SQL migrations, disaster-recovery exercises, backups, alerting, SIEM/monitoring and availability protections.
- Object storage with malware scanning and sandboxed document parsing; virus scanning of uploads; stronger cache/CDN and reverse-proxy-based rate limits.
- Hardware-backed key custody, key rotation, and **standards-based PDF digital signatures / PKI** if legally required. HMAC signs registry metadata but is *not* a PDF digital signature. Public QR verification alone cannot prevent QR-copy attacks—verifiers must compare printed fields with the trusted server record.
- Verified payment processor / bank reconciliation / invoices / tax logic (this demo uses **manual review**, no money is automatically charged).
- Full localization QA with native Pashto/Dari speakers, printer and accessibility tests; official seals/branding validation.
- For high-throughput batch issuance use background workers with job tracking (this implementation limits synchronous CSV batches to 100).
- Public verification discloses recipient and award by default; consult privacy/legal policy and adapt disclosures for sensitive credentials.
- Secure password rotation and account lockouts, CSRF header for any future JSON API, audit-retention controls and tamper-evident externally persisted audit logs.

## Tech

Python 3.13+; FastAPI + Starlette; SQLAlchemy; Jinja2 and vanilla JS/CSS; Argon2id; WeasyPrint; QRCode; Pillow and pypdfium2; PostgreSQL via psycopg in Docker (SQLite for local experiments); containerized deployment.

## Automated testing

```bash
python -m pytest -q
```

For government deployments, prefer a separated staging environment with real Arabic script fonts and exact target browsers/printers. `APP_SECRET` and `CERT_SIGNING_KEY` must remain stable and protected between deployments: changing the signing key will cause existing certificates to fail integrity validation.
