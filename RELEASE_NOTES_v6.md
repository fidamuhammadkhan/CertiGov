# CertiGov v6 — Certificate Drafts, Safe Corrections, Archiving, and Designer Usability

**Release date:** 2026-11-23
**GitHub:** https://github.com/fidamuhammadkhan/CertiGov
**Live service:** https://certigov-platform.onrender.com

## Implemented changes

1. **Editable certificate drafts** (`/certificates/drafts`). Issuers and organization administrators can prepare, save, reopen and delete *unissued* work. A draft has no serial, cryptographic signature, public QR or impact on subscription issuance counts. Draft access is limited to its creator or the organization administrator.
2. **Correction & reissue for issued certificates.** Organization admins can open `/certificates/<id>/correct`, review/edit the fields and create a replacement. Issuance signs a **new** record and creates a new serial/QR. The original remains in the registry, is marked **revoked**, and links to the replacement via separate lifecycle metadata. Its signed payload and original PDF are preserved. Reissue requires an active subscription/remaining quota. Transactional issuance prevents partial correction.
3. **Archiving/restore.** An organization admin may archive issued records to hide them from default search results or restore them. Archive metadata lives separately from the signed claims and does not change QR verification status. Certificate search and CSV export have a Visibility filter.
4. **Duplicate as draft.** Organization issuers/admins can copy the details of an issued certificate into a new, editable draft without modifying the original.
5. **Certificate actions.** The list has Show, PDF and More (Correct, Duplicate, Revoke, Archive/Restore); no destructive Delete for signed records. The detail view also offers these actions where permitted.
6. **Designer fixes.** Long controls now wrap in a responsive grid instead of colliding. Designer has a field selection dropdown, explicit custom-variable key/label inputs, a layer list, highlighted current element and a drag handle for resizing. The first QR element is auto-selected, and Save is accessible in the preview toolbar.
7. **Uploaded artwork.** Imported page defaults to white to prevent colored bars around mismatched scans. New uploads can auto-detect portrait/landscape orientation. The existing designer has a Match paper orientation control. Other elements/variable text are only added deliberately.
8. **Public correction verification.** QR scans of a revoked original indicate its replacement and link to the new public verification record.
9. **Additional testing.** V5 regression, three original Pytest tests, v6 draft/correction/archive/role tests and offline Chromium visual checks at 1600px and 410px viewports.

## Schema and data preservation

Only two **new** tables are created automatically by `Base.metadata.create_all()` at application startup:

- `certificate_drafts`: organization-scoped, editable pre-issuance values and optional photo reference
- `certificate_record_states`: archive/replacement metadata separate from immutable signed certificate claims

No existing certificate row/column is dropped or rewritten by migration. No deletion of users, subscriptions, PDF blobs, organizations, templates or old certificates is required. A no-compute Neon branch was created before the live deployment as a safety snapshot.

## Limitations / responsibilities

- A correction deliberately issues another certificate and counts against the organization's subscription. The old certificate becomes revoked and is retained for audit.
- The system does not produce PDF signatures from a government-recognized certificate authority. QR verification checks the application's own database/signing integrity.
- Importing a finished diploma/third-party certificate does **not** convert its printed content into editable variables. Use authorized **blank** artwork and placeholders for real issuance.
- For production use with sensitive student data, implement administrative MFA, lifecycle-aware backups, incident monitoring and a formal data-retention policy.
- Historical PDF integrity is preserved during archive/reissue; existing PDFs are not silently edited.
