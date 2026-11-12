# CertiGov v2 — Free public HTTPS deployment (Render + Neon)

**Deployment status:** Ready-to-deploy source. There is **no public live instance** until you deploy it in your own accounts. The URLs below are provider dashboards, not your application's URL.

## A. English: first public installation

**Purpose:** A no-cost demonstration system with an HTTPS URL that phones can open by scanning the QR code. For official certificates, move to paid, backed-up infrastructure and complete a security/legal review before real issuance.

### 1. Create a free persistent database

1. Visit **https://console.neon.tech/** and create a free account/project named `certigov`.
2. Click **Connect** and copy the PostgreSQL connection string, including the `?sslmode=require` part. It normally starts with `postgresql://`. Do **not** publish or paste this value into GitHub or a public chat.
3. Keep that connection string private. CertiGov automatically adapts the `postgresql://` prefix for its psycopg v3 driver.

### 2. Put this app in a private GitHub repository

1. Visit **https://github.com/new**, create a private repository named `certigov-platform`.
2. Extract the ZIP download on your computer. Upload the **contents of the `CertiGov_Platform` directory**, not the outer ZIP file. The root of the GitHub repository must directly contain `render.yaml`, `Dockerfile`, `start-render.sh`, `app/`, and `requirements.txt`.
3. Do **not** upload `.env`, `data/`, test databases, personal PDFs, password files, or database connection strings. `.env.example` is safe because it contains placeholders only.

### 3. Deploy the web application on Render (free)

1. Open **https://dashboard.render.com/** and create a free account.
2. Connect your GitHub account to Render. Choose **New → Blueprint**, and choose the `certigov-platform` repository. Render will detect `render.yaml`.
3. Review that **CertiGov web service = Free** and no paid resources or optional addons are selected.
4. Enter three required secret values when prompted:
   - `DATABASE_URL`: the Neon connection string from step 1.
   - `INITIAL_ADMIN_EMAIL`: an email address that you control.
   - `INITIAL_ADMIN_PASSWORD`: a unique password containing **at least 12 characters**.
5. Confirm and deploy. Render automatically creates two independent signing/session secrets and supplies `RENDER_EXTERNAL_URL` (the application's permanent HTTPS address).
6. When the service shows **Live**, open the actual URL provided by Render, such as `https://your-service-identifier.onrender.com`. This example is **not** an existing deployment.
7. Sign in with the administrator email and password from step 4. Open **My Profile** and change the password. Then remove `INITIAL_ADMIN_PASSWORD` from Render's environment settings; it is only needed for the first bootstrap.

### 4. Test certificate QR verification on a different phone

1. Super Admin → **Organizations** → create a university/school/department with its own administrator.
2. Organization Admin → **Templates** → select one of the catalog designs, optionally upload a background and save it.
3. Organization Admin → **Billing** → request a plan. Super Admin → **Billing** → approve the request. These demo approvals **do not charge money**.
4. Organization Admin → **Issue Certificate** → generate a certificate → download its PDF.
5. Open/print the PDF and scan its QR from a **different device**, preferably using mobile data (not your development computer). The URL must start with your actual `https://...onrender.com/verify/` domain.
6. The page should display the **issued certificate's live status and details**. From the organization portal revoke a **test** certificate and scan the same QR again; the page must now report **revoked**.
7. For a certificate created with the *old local/private QR URL*, open that certificate's detail page as the organization administrator and click **Regenerate PDF with live QR**. Download and **reprint/re-distribute the newly generated PDF**. The old printed code cannot be fixed remotely.

### Important limitations of free hosting

- Render's free web services go idle after 15 minutes without requests, and the first QR verification after idle may take about a minute to respond. Cold starts make this **unsuitable for high-assurance government use**.
- Render free app instances have an ephemeral filesystem. This edition uses `STORAGE_BACKEND=database` to retain uploaded images and PDFs in the **Neon PostgreSQL database** instead.
- Neon Free storage is limited (currently 1 GB per project), so storing PDF files in PostgreSQL is **for pilot volumes only**. Plan private object storage and backups before high-volume rollout.
- The platform provides QR-backed *registry verification*, not cryptographic PDF signing with a trusted certificate authority. Formal government/academic use requires due diligence and potentially legally recognized electronic signatures.
- Free services change limits and availability. Check current plans before deployment. Do not enter official or sensitive personal documents during the pilot.
- Keep `APP_SECRET`, `CERT_SIGNING_KEY`, the Neon database, and your service name stable. Rotating the certificate signing key without a migration plan invalidates prior integrity checks.

### Troubleshooting

| Symptom | Fix |
|---|---|
| The QR opens `127.0.0.1` or `testserver` | The PDF was issued before public deployment. Click **Regenerate PDF with live QR** and download/reprint it. |
| The QR leads to a public HTTPS site but shows "not found" | Ensure the same persistent Neon database is still connected and no token was changed; compare with the public URL displayed in certificate details. |
| Render shows database connection error | Verify the entire Neon connection string, its database user, and SSL parameters in Render's secret `DATABASE_URL`. |
| Render is slow after inactivity | This is expected on its free service. It can take about one minute to restart. |
| Uploaded images disappear | Confirm `STORAGE_BACKEND=database` and that you are using the persistent Neon database. |
| No super admin exists | Check `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` and redeploy; only the first account is automatically bootstrapped. |

**Provider sources:** https://render.com/docs/free , https://render.com/docs/blueprint-spec , https://render.com/docs/environment-variables , https://neon.com/docs/introduction/plans , https://neon.com/docs/get-started/connect-neon

---

## B. پښتو: وړیا انلاین فعالول

۱. په **https://console.neon.tech/** کې وړیا PostgreSQL ډیټابېس جوړ کړئ او د `Connect` له برخې څخه د اتصال پټ ادرس (DATABASE_URL) واخلئ. دا ادرس له نورو سره مه شریکوئ.

۲. په **https://github.com/new** کې شخصي (Private) Repository جوړ کړئ. د ZIP فولډر خلاص کړئ او د پروژې ټولې فایلونه (لکه `render.yaml` او `Dockerfile`) پورته کړئ؛ `.env` او اصلي معلومات مه پورته کوئ.

۳. په **https://dashboard.render.com/** کې حساب جوړ کړئ. خپل GitHub وصل کړئ، **New → Blueprint** وټاکئ او د CertiGov پروژه انتخاب کړئ. د خدمت **Free** پلان تایید کړئ.

۴. درې معلومات تنظیم کړئ: `DATABASE_URL` (د Neon ادرس)، `INITIAL_ADMIN_EMAIL` (ستاسو ایمیل)، او `INITIAL_ADMIN_PASSWORD` (له ۱۲ تورو اوږد قوي پټنوم). نورې پټې کیلي Render په اتومات ډول جوړوي.

۵. چې پروژه **Live** شي، د Render ورکړل شوی `https://...onrender.com` ادرس پرانیزئ. د عمومي مدیر په توګه ننوځئ. اداره او د هغې کارن جوړ کړئ، بسته فعاله کړئ او نوی سند صادر کړئ.

۶. د سند PDF په موبایل کې د QR په وسیله سکین کړئ. باید د سند **عامه تایید پاڼه** پرانیستل شي. که په پخواني سند کې `127.0.0.1` وي، د سند په تفصیلاتو کې **Regenerate PDF with live QR** ووهئ او نوی PDF چاپ کړئ.

**احتیاط:** وړیا کوربه‌توب د ازمایښتي کار لپاره دی، نه د رسمي دولتي سندونو لپاره. له ډېرې بې‌کارۍ وروسته د QR پاڼې پرانیستل ځنډېدای شي. د دولت لپاره پیاوړې امنیتي کتنه، بیک‌اپ او باوري ډیجیټل امضا اړین دي.

---

## C. دری: راه‌اندازی رایگان روی اینترنت

۱. در **https://console.neon.tech/** یک دیتابیس رایگان PostgreSQL ایجاد کنید و رشته اتصال `DATABASE_URL` را از بخش **Connect** دریافت نمایید. این اطلاعات محرمانه است.

۲. در **https://github.com/new** یک مخزن **Private** بسازید. فایل‌های استخراج‌شده پروژه، از جمله `render.yaml` و `Dockerfile` را به مخزن اضافه کنید. فایل `.env`، پسوردها و اطلاعات واقعی کاربران را بارگذاری نکنید.

۳. به **https://dashboard.render.com/** بروید، GitHub را متصل کنید و **New → Blueprint** را انتخاب نمایید. مخزن CertiGov را انتخاب کنید و اطمینان حاصل کنید که پلان سرویس **Free** است.

۴. `DATABASE_URL` (از Neon)، `INITIAL_ADMIN_EMAIL` (ایمیل مدیر کل) و `INITIAL_ADMIN_PASSWORD` (رمز قوی حداقل ۱۲ حرف) را وارد کنید. Render کلیدهای محرمانه دیگر را به صورت خودکار می‌سازد.

۵. پس از نمایش حالت **Live**، آدرس HTTPS داده‌شده توسط Render را باز کنید. به‌عنوان مدیر کل وارد شوید، یک نهاد و حساب کاربری آن را ایجاد کنید، اشتراک را تأیید و تصدیق‌نامه جدید صادر نمایید.

۶. PDF را روی موبایل توسط QR اسکن کنید. باید صفحه اعتبارسنجی عمومی تصدیق‌نامه باز شود. برای تصدیق‌نامه‌های قدیمی دارای آدرس `127.0.0.1`، گزینه **Regenerate PDF with live QR** را در جزئیات سند انتخاب کرده و نسخه جدید را چاپ کنید.

**هشدار:** هاست رایگان فقط مناسب آزمایش است، نه صدور رسمی مدارک دولتی. نخستین اسکن پس از غیرفعال‌شدن سرویس ممکن است با تأخیر باز شود. قبل از استفاده رسمی، ارزیابی امنیتی، پشتیبان‌گیری و امضای دیجیتال مورد اعتماد لازم است.
