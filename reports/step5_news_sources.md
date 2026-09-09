# STEP 5 news sources audit

probed 2026-09-09; provider abstraction in news/providers/

| provider | official | exchanges | availability | historical depth | timestamp quality | mapping | rate limit | duplicate rate | content quality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sse | yes | SH | OK (bulletin index lags ~5 days) | ~2015+ (2014 sparse) | per-second | 6-digit code | ~100/page, polite single-connection | low (official) | title-only (content on demand) |
| szse | yes | SZ | OK | 2018+ deep | per-second | 6-digit code (list field) | 30/page | low (official) | title-only |
| cninfo | no | SH+SZ | OK | 2000s+ | epoch-ms | code+orgId derivable | 30/page | medium (reprints) | title+adjunct URL |
| akshare | no | SH+SZ | WAF-intermittent (eastmoney) | deep | date-only | code field | unknown | medium | title-only |

Policy: official exchanges first; a blocked source is recorded SOURCE_BLOCKED and the next legal source is used. No proxy pools, no WAF bypass, no high concurrency.
