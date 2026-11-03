# Daily Genesys report — 17:00 Germany time

**What changed:** The optional API workflow is now scheduled for 17:00 `Europe/Berlin` daily (DST-aware). When `GENESYS_CLIENT_ID` or `GENESYS_CLIENT_SECRET` is missing, it skips collection without publishing fake data. Its reporting period is Germany local midnight through collection time.

## Alternative without OAuth: upload a queue-only CSV

Genesys Cloud can export Performance views as CSV, if your user has Analytics Data Export permissions. Under Analytics Workspace, open **Queue Performance**, select:
- Queues **Ger-On-Site** and **GER_Installer** only
- Media type **Voice**
- Date **Today** (German local reporting time zone)
- Columns **Offered**, **Answered**, **Abandoned**

Export CSV. Because Genesys export column naming/localization can differ, prepare a tiny *normalized* CSV with these exact column names:

```csv
report_date,queue_name,offered,answered,abandoned
2026-11-03,Ger-On-Site,100,80,10
2026-11-03,GER_Installer,50,44,4
```

The numbers above are **examples only**; replace with actual export totals.

1. Create or edit `imports/genesys_daily.csv` in your GitHub repository, using **Add file → Create new file** or **Upload files** on `main`.
2. Commit. The **Import Genesys CSV to AEDATS** workflow will validate the two rows and build `data/genesys.json`. The Pages dashboard will read it.
3. Check the workflow logs if it fails (for example, invalid column names or missing queue).

**No OAuth Client, API credential or server is required for the manual CSV path.** However, *GitHub cannot automatically sign into Genesys* or retrieve a protected CSV on its own. For truly automated daily export, arrange with a Genesys admin for either a read-only OAuth Client or scheduled export delivery to an approved service.

## Privacy and data interpretation

Your GitHub repository and GitHub Pages website are PUBLIC. Commit only **aggregate queue totals** to the public repository. Never commit named employee metrics, raw interactions, conversation identifiers, customer data, OAuth secrets or protected export URLs.

With CSV import:
- Offered/Answered/Abandoned and Answer Rate are available for the exported period.
- Current waiting number, longest current wait and ASA are **not provided** by this simplified CSV schema; the dashboard shows placeholders rather than inventing numbers.
- This is a daily snapshot, not real-time monitoring.
- The API-based workflow can still populate waiting status at its daily 17:00 snapshot, if credentials become available.

For exporting agent-specific workload of DA Service / yechuan.chen, use a company-private channel, not public GitHub Pages.
