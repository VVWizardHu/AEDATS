# Genesys Cloud Ireland → AEDATS (GitHub Actions)

This integration adds a bilingual Genesys panel to the existing AEDATS dashboard without replacing CRM or the original Hotline section.

**Queues:** `Ger-On-Site`, `GER_Installer` (voice only).
**Rolling window:** last 30 minutes for offered, answered, abandoned, answer rate and ASA.
**Live snapshot:** waiting, interacting, alerting and (when observation details permit) longest current wait.

## Configuration (required before real data appears)

1. Merge the deployment pull request into `main`.
2. In GitHub repository **Settings → Secrets and variables → Actions**, create secrets:
   - `GENESYS_CLIENT_ID`
   - `GENESYS_CLIENT_SECRET`
3. Grant the Genesys OAuth Client Credentials role visibility of the target divisions and permissions: `routing:queue:view`, `analytics:queueObservation:view`, `analytics:conversationAggregate:view`.
4. In GitHub **Actions**, manually run **Genesys queue snapshot** on `main`, inspect logs, and verify `data/genesys.json` was committed. Ensure workflow permissions allow `contents: write`. Existing branch protection may require an exception for the bot.
5. Open `https://vvwizardhu.github.io/AEDATS/`. The page fetches the JSON every minute. Cron is scheduled every 5 minutes but can be delayed.

## Privacy

The repository and GitHub Pages content are public. Personal agent workload is **NOT published by default**. Enabling `PUBLISH_PERSONAL_WORKLOAD=true` is appropriate only if your company explicitly authorizes publishing the named users' performance data to the entire internet, including permanent Git history. If you need private per-agent metrics, use a private dashboard or authenticated backend rather than Pages.

Optional agent identities (when allowed): `DA Service`, `yechuan.chen`. Personal data lookup additionally requires `directory:user:view`.

The dashboard contains **no Genesys Client Secret**, tokens, raw conversations or customer data.

## Operational behavior

- GitHub Pages does **not** provide 15-second real-time monitoring. This is delayed snapshot reporting.
- Data older than 15 minutes are displayed as stale and the indicators are suppressed.
- If Genesys authentication fails, the collector exits and leaves the last successful JSON unchanged.
- Queue/user identity names are resolved to unique Genesys IDs; duplicates or absent names cause an error.
- Observation detail-based longest wait may be missing or incomplete. It is not a guaranteed global max.
- The older static Hotline bars remain unchanged; the new panel is separate until someone explicitly replaces their data source.
