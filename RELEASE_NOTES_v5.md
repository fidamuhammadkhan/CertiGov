# CertiGov v5 — Certificate taxonomy, visual designer and management actions

Release date: 2026-11-23. This release is an additive upgrade of the existing CertiGov installation. Existing certificate serials, signed payloads, PDFs and verification tokens are preserved.

## Changes

1. **Platform plans:** View, edit, archive/restore and safely delete unused plans. A plan with subscription history is archived rather than removed. An active subscription's maximum quota cannot be silently changed by editing a plan.
2. **Management actions:** View/Edit/Archive/Safe Delete or disable relevant entities in platform organizations, users, subscriptions, organization team, certificate templates, messages and organization certificate categories. Security- and audit-relevant records are not destroyed when history depends on them.
3. **Approval and CSRF:** Subscription approval/rejection requests are idempotent and redirect to a stable list route, avoiding stale/repeated-action errors. JavaScript refreshes the session-bound CSRF token immediately before posting, while server-side validation remains compulsory. A genuinely missing token remains a 403.
4. **Certificate designer:** Drag, move, resize, layer, rotate and adjust opacity of certificate text, logos, signatures, recipient photos, lines, masks and the live QR code. Upload blank artwork or use a catalog design. Define reusable custom fields (e.g., student ID, faculty, course, batch) using `{{field:student_id}}` placeholders. Templates belong to one organization.
5. **Certificate issuance:** Choose an organization-defined certificate category, upload an individual recipient portrait for templates containing a Photo field, enter dynamic fields, and issue signed PDF certificates. Bulk CSV supports categories and custom variables; individual portrait upload is not part of bulk CSV.
6. **Search and reporting:** Filter certificates by recipient/serial/award/program, organization-defined category, template, date range, language and status. Export filtered certificate data as a CSV (with spreadsheet-formula protection) and use paginated results.
7. **Safeguards:** Tenant isolation, archive-before-delete behavior, immutable issued records, audit logging, preserved verification signatures for old certificates, safe upload checks and schema validation remain in place.

## Production schema changes

- Creates `certificate_categories` table with organization-scoped unique category codes.
- Adds nullable `certificates.category_id` referencing the category table, plus an index.
- `initialize_database()` applies the column/index change idempotently on startup. Existing certificates keep `category_id = NULL` and their original signed payload format. No destructive data migration is performed.

## User workflows

Super Admin: Plans → View/Edit/Archive/Restore/Delete safely; Organizations/Users → record actions; Subscriptions → Approve/Reject/Cancel. Organization Admin: Categories → Create/Edit/Archive/Restore/Delete safely; Templates → Designer → Add recipient photo, logo or custom field; Issue Certificate → Select category/template, provide recipient photo and variable values; Certificates → filter/export/view/download/revoke.

## Verification and known limitations

- Automated regression tests: `python -m pytest -q` and `python tests/v5_smoke.py`.
- JavaScript syntax check: `node --check app/static/designer.js`, `app/static/app.js` and `app/static/issue.js`.
- Non-destructive live rollout: preserve `DATABASE_URL`, `APP_SECRET` and `CERT_SIGNING_KEY` on Render; deploy the exact GitHub source commit; check the Render deploy status, logs and Neon table counts.
- Issued certificates are immutable. Edit/delete of an issued certificate is intentionally unavailable; authorized staff may revoke while retaining the audit trail.
- A portrait is an optional per-certificate upload for templates that use a Photo element. Each student portrait must be uploaded by an authorized issuer; the public verification page does not expose that image.
- The interface is a percentage-positioned 2D certificate design studio, not a 3D modeling application or a replacement for professional vector graphics software.
- The platform provides registry-based QR verification and HMAC integrity checks; it is not an accredited certificate-authority PDF signature service.
