# CertiGov v6 — Organization Operator Guide

## A. Design an original certificate

1. Log in as **Organization Admin** or **Designer** and open **Templates**.
2. Select a built-in design, or choose **Import your own certificate** to upload an organization-authorized **blank** JPG, PNG or PDF. PDF imports convert the first page to an image.
3. Prefer **Auto-detect uploaded artwork** when importing. Existing templates can use **Match paper orientation to uploaded artwork**.
4. In the designer's **Add elements** section, choose a field such as Recipient name, Program, Award, Certificate category or Serial, and click **Place selected field**. These placeholders are resolved from real issuance values.
5. Add optional Student Photo, Organization Logo, Signature or QR elements. Click and drag to position. Drag the small blue corner handle to resize, or use exact position/size properties.
6. To request additional student-specific information, type a field key (e.g. `student_id`) and a label (e.g. `Student ID`), then click **Add custom field**. The issuer will see an input for this value. The placeholder is `{{field:student_id}}`.
7. Open **Certificate layers** to select an element that is difficult to click. Use Bring forward / Send backward for ordering, and the properties panel for appearance.
8. Click **Save design**. Create a **fictional** test certificate, check the actual PDF and scan its QR link.

**Important:** Uploaded scans are raster backgrounds. Any words, seals or signatures already printed in the image are not separate editable data fields. For legitimate certificates, request a clean blank design from the issuing institution. Avoid using existing issued credentials as a reusable template.

## B. Prepare and save a draft

1. Open **Issue Certificate**, choose a template/category and enter known recipient fields.
2. Click **Save editable draft**, even if you have not completed all fields.
3. Visit **Certificate Drafts** to edit or delete the unissued record later.
4. Click **Issue certificate & QR** only after checking all data and confirming subscription capacity. Draft issuance creates the first signed PDF and public QR record.

A draft is private to its creator and the organization's administrator. Drafts have no public verification address, issued serial or subscription usage.

## C. Correct an already-issued certificate

1. Open **Certificates** and find the certificate using name, serial, category, dates, template, language or status.
2. Choose **More → Correct & reissue** (Organization Admin only). The old values load into the form.
3. Fix the recipient/award/date/photo/variable values, check the selected design, then issue.
4. CertiGov produces a new serial/QR and PDF, **revokes the original**, and logs the old-to-new replacement link. The old certificate remains available in audit history and old QR scans show its revoked status.

Never rewrite the signed fields of an already-issued record in place. Corrections require a valid subscription and consume an issuance allowance.

## D. Duplicate, archive and restore

- **Duplicate as draft:** Copies the fields of an existing certificate to a new unissued draft; the original remains valid.
- **Archive record:** Organization Admin hides a signed certificate from ordinary search results. A certificate that is archived but otherwise valid still verifies as valid by QR.
- **Restore record:** Show it again in normal searches. Use the **Visibility → Archived records** filter to find archived certificates.
- **Revoke:** Stops the existing certificate from verifying as valid. This cannot be undone through an ordinary interface.
- **Delete:** Only available for unissued drafts. Issued, signed credentials retain their history.

## E. Presentation checks

Use fictional names and demo-only accounts for the IT Expo. Try Pashto/Dari toggles, light/dark themes, a test category, custom variable field, a fictional student portrait, draft saving, a corrected sample and two different QR verification results (valid and revoked).
