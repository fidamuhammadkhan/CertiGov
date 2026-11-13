# CertiGov v4 — Full RTL localization, accessible themes, imported-artwork certificate fidelity

## What changed

1. **Pashto and Dari public content now actually changes.** The public homepage, About, Contact, Plans and Signup pages include translated headings, paragraphs, calls to action and navigation. The selected language is stored in the existing signed session. Native HTML `lang` and `dir=rtl` match the language; no machine translation or external service is required. English remains available.
2. **Administrator-controlled translated content.** Super Admin → Website Studio offers optional Pashto and Dari versions of the tagline, hero, About content, purpose, and mission. The system uses a built-in translation of standard English text where no override is supplied. Custom English text that differs from the standard defaults must be translated using these fields to be correct in all languages.
3. **12 dashboard/public-site color themes.** Ocean, Midnight, Emerald, Rose, Violet, Sand, Sunset, Forest, Slate, Azure, Copper, and Graphite. A light/dark switch appears in the top bar on every page and authenticated dashboard. Users' choices are saved to local browser storage; administrators can set the default for new visitors in Website Studio. The contrast of form fields, menus, tables, cards and headers has been improved.
4. **Imported artwork: QR-only by default.** When an organization uploads a JPG/PNG or first PDF page, CertiGov preserves the artwork without adding a second title, university logo, student name, serial, or date. Only a movable public QR verification code is added by default. It is now possible to add named certificate placeholders, text, lines, and cover rectangles manually in the editor.
5. **Existing imported templates.** The template editor offers **Reset uploaded design to QR only**. This modifies only the template configuration, not already-issued certificates. Previously issued certificates retain their immutable snapshots; correcting an official document requires reviewed issuance of a new corrected document, not rewriting verification history.
6. **Background fitting and QR scanning.** Choose Fit entire artwork (default, preserves the source aspect ratio), Fill page and crop, or Stretch to page (distorts the art). QR elements have a minimum display width to support reliable PDF scanning.

## Important caveat about the uploaded University of Haripur PDF

The supplied example is an already-completed certificate with preprinted university name, seals, recipient details, date, signatures and fine print in the original image. Those characters are raster background pixels, **not editable CertiGov text**. Uploading that finished certificate as a template will retain every preprinted detail unless the institution supplies a blank master or an operator covers selected regions. Rectangular color masks cannot reconstruct complex ornamental paper patterns or reliably erase textured text. Use a clean, authorized blank institution certificate for professionally accurate variable data.

## Privacy, security and history

The release does not change authentication keys, passwords, organization ownership, subscription status, the certificates table, or existing issued records. It adds no database tables or columns. Theme preferences are saved only in each browser (the server-side administrator default is stored in existing `website_settings.values` JSON). Uploads remain organization-scoped and sanitized; QR verification still uses HTTPS and the permanent certificate record. Do not place real credentials or preprinted personal information in a reusable template without authorization.

## Test and deployment

- Run `python -m pytest -q` for the existing and new integration tests.
- Run `STORAGE_BACKEND=database python -m pytest -q` to verify database-backed image/PDF storage.
- Tested responsive UI at 1440px and 390px, both RTL languages, light/dark themes, and a dark Super Admin dashboard using a headless browser.
- Deploy from the existing GitHub repository to the existing Render free Docker service (auto deploy disabled; trigger after publishing).
- Existing users may need a hard refresh for the new `style.css?v=4` and `app.js?v=4` assets. Browser-local theme choices are stored under new v4 keys.
