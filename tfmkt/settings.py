# -*- coding: utf-8 -*-
BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

FEED_FORMAT = 'jsonlines'
FEED_URI = 'stdout:'

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
   'scrapy.extensions.closespider.CloseSpider': 500
}
DOWNLOADER_MIDDLEWARES = {
   'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 500
}

CLOSESPIDER_PAGECOUNT = 0

# --- Throughput (single domain via Zyte SmartProxy) ---
# Every request goes to transfermarkt.* through the Zyte proxy. Raising per-domain
# concurrency 8->16 was tried and REVERTED: a full prod run (2026-07-13) showed it
# made the scrape SLOWER (domestic-clubs crawl ~65 min vs ~55 min at 8) — at higher
# concurrency Transfermarkt bans harder, Zyte throttles harder (driver-log showed
# response/banned + reset_backoff:149), so net throughput drops. The real bottleneck
# is Zyte's ban-based throttling, not the concurrency ceiling; the job-timeout bump
# to 90 min (db-ingestion) is the actual safeguard. Keep concurrency at the default 8.
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_TIMEOUT = 60          # default 180s — stop one hung request stalling the crawl
RETRY_TIMES = 3               # default 2; 429/503 already in RETRY_HTTP_CODES.
                              # Keep modest: scrapy-zyte-smartproxy already retries
                              # Zyte bans (503) with its own backoff.

# --- AWS WAF challenge mitigation (prod incident 2026-07-15) ---
# Transfermarkt (CloudFront) started serving an AWS WAF JavaScript challenge as
# HTTP 202 with `x-amzn-waf-action: challenge` and a ~2.4KB challenge page body.
# Zyte's transparent proxy mode (api.zyte.com:8011) passes the 202 through
# unsolved. Scrapy treats any 2xx as success — no retry — so spiders parse the
# challenge HTML and silently yield 0 items. In the 2026-07-15 06:00 prod run
# the competitions crawl collapsed from 392 items (2026-07-13) to 9 (6 of 16
# responses were 202), and task 03b_scrape_games then died on an empty
# games_urls.json. The challenge is applied per Zyte exit IP (measured 202 rate
# 6-40% per request), so retrying through a fresh exit usually succeeds:
# a live probe needed 4 attempts (202,202,202,200) in the worst case observed.
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 202]

# The HTTP cache stores any response by default — including the 202 challenge
# page — and serves it back to retried requests (cache runs before the retry
# middleware sees the response), which would defeat the retry loop entirely.
# Never cache WAF-challenged responses.
HTTPCACHE_IGNORE_HTTP_CODES = [202]

# Do NOT enable AUTOTHROTTLE: with a rotating proxy, high per-request latency is
# normal and AUTOTHROTTLE would misread it and throttle concurrency *down*.

LOG_LEVEL = 'INFO'            # was 'ERROR' — surfaces retry warnings + end-of-run
                              # stats (retry/count, response_status_count/503,
                              # finish_reason) that were previously suppressed.
LOGSTATS_INTERVAL = 60.0      # per-minute request/item throughput line

# HttpCacheMiddleware settings
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = 'httpcache'

# https://docs.scrapy.org/en/latest/topics/request-response.html?highlight=REQUEST_FINGERPRINTER_IMPLEMENTATION#std-setting-REQUEST_FINGERPRINTER_IMPLEMENTATION
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
