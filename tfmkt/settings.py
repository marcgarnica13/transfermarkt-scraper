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
# Every request goes to transfermarkt.* through the Zyte proxy, so the real
# concurrency ceiling is the *per-domain* limit (Scrapy default 8). At default 8
# the prod competitions+clubs scrape (~4k requests) sustained only ~1 req/s and
# crossed its 60-min job timeout. Raise both to 16 for headroom.
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 16
DOWNLOAD_TIMEOUT = 60          # default 180s — stop one hung request stalling the crawl
RETRY_TIMES = 3               # default 2; 429/503 already in RETRY_HTTP_CODES.
                              # Keep modest: scrapy-zyte-smartproxy already retries
                              # Zyte bans (503) with its own backoff.

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
