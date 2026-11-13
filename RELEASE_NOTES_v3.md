# CertiGov v3 — Public registration, website studio and design library

## New visitor experience
- Public marketing homepage, `/plans`, `/signup`, `/about`, and `/contact`.
- Dynamic public plans come directly from currently active Plan rows.
- Organization signup creates tenant, org-admin user, and a **pending** subscription; no payment is taken and certificate issuance remains blocked until superadmin approval.
- Contact inquiries and registration notices are stored in a private admin inbox at `/admin/messages`. No outbound email is claimed.

## Superadmin website studio
- `/admin/website`: brand label, logo initials, hero text, about text, mission, why verification matters, contact information, social links, primary/accent/background colors, and hero/font style presets.
- Social URLs are restricted to HTTPS. All user-provided text is HTML-escaped by Jinja2 and CSS colors are validated.
- New `website_settings` and `website_messages` tables are created automatically when the app starts. Existing certificates and users are retained.

## Certificate design
- `/templates/import`: an explicit first-class route to upload a full certificate background in PNG/JPEG/PDF format, then edit overlaid fields. PDF page 1 is rasterized to a PNG before private database storage.
- 10 different composition families with location and hierarchy changes, 5 frame types, 10 palettes and 5 decor treatments (palette-based). Template editor now offers artwork treatments.
- The designer continues to produce a PDF with embedded scan-ready verification QR.

## Important boundaries
- New organizations are not approved for issuance automatically. An administrator must review and approve the subscription.
- Free-tier hosting sleeps, and storing PDFs in Postgres is only appropriate for a pilot.
- Site messages are stored on the server, not sent by email. SMTP delivery, anti-bot challenge/CAPTCHA, double opt-in and email verification are recommended before public production registration at scale.
- This remains a QR-backed registry, not a CA-issued legally recognized digital signature.
- The new website admin theme controls are layout presets, not an unrestricted HTML page-builder.
