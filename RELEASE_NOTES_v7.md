# CertiGov v7 — template designer usability and blank-preview fix

- Add versioned `designer.js?v=7` so new templates do not load an older cached editor bundle.
- Show **Editor ready** status, element count and descriptive errors instead of silent initialization failure.
- Provide preview-only sample recipient, organization, award, course and date inputs. These values never become real certificate records.
- Let organization designers preview custom-variable values before issuing a certificate.
- Explain exactly how to place fields and use the canvas/resize/layers.
- Show an empty-state message if all layers are invisible.
- Reduce unnecessary ResizeObserver paints to stabilize dragging and resizing.
- Improve new catalog template default positions and align QR element dimensions with sanitized PDF settings.
- Add desktop/mobile and backend regression tests. Existing issued records remain unchanged.

The preview QR is an editor symbol, not a scannable issued certificate. Real QR codes are generated when a credential is issued. Use only fictional data when demonstrating.
