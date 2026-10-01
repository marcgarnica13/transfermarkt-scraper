"""Offline tests for ClubsSpider squad-URL construction (DAT-291)."""
import os

from scrapy.http import HtmlResponse

os.environ["SCRAPY_CHECK"] = "1"

from tfmkt.spiders.clubs import ClubsSpider  # noqa: E402

PARTICIPANTS_HTML = """
<html><body><div class="responsive-table"><table>
<thead><tr><th>club</th></tr></thead>
<tbody>
<tr><td></td><td><a href="/trau-fc/startseite/verein/36765/saison_id/2025">TRAU FC</a></td></tr>
<tr><td></td><td><a href="/platense-ii/startseite/verein/99999/saison_id/2025">Platense II</a></td></tr>
</tbody></table></div></body></html>
"""


def _squad_urls(tmp_path, season=None):
    parents = tmp_path / "parents.json"
    parents.write_text("")
    spider = ClubsSpider(parents=str(parents))
    if season:
        spider.season = season
    response = HtmlResponse(
        url="https://www.transfermarkt.co.uk/some-league/startseite/wettbewerb/XX1",
        body=PARTICIPANTS_HTML.encode(),
        encoding="utf-8",
    )
    return [r.url for r in spider.parse(response, parent={})]


def test_squad_url_drops_pinned_season_when_season_not_requested(tmp_path):
    assert _squad_urls(tmp_path) == [
        "https://www.transfermarkt.co.uk/trau-fc/kader/verein/36765/plus/1",
        "https://www.transfermarkt.co.uk/platense-ii/kader/verein/99999/plus/1",
    ]


def test_squad_url_keeps_season_when_explicitly_requested(tmp_path):
    assert _squad_urls(tmp_path, season="2025") == [
        "https://www.transfermarkt.co.uk/trau-fc/kader/verein/36765/saison_id/2025/plus/1",
        "https://www.transfermarkt.co.uk/platense-ii/kader/verein/99999/saison_id/2025/plus/1",
    ]


def test_older_season_rows_for_same_club_are_still_skipped(tmp_path):
    """Pins existing season-dedupe: a club listed under 2026 and 2025 is requested once."""
    html = """
    <div class="responsive-table"><table><thead><tr><th>club</th></tr></thead><tbody>
    <tr><td></td><td><a href="/a/startseite/verein/1/saison_id/2026">A</a></td></tr>
    <tr><td></td><td><a href="/a/startseite/verein/1/saison_id/2025">A (previous season)</a></td></tr>
    </tbody></table></div>
    """
    parents = tmp_path / "parents.json"
    parents.write_text("")
    spider = ClubsSpider(parents=str(parents))
    response = HtmlResponse(
        url="https://www.transfermarkt.co.uk/some-league/startseite/wettbewerb/XX1",
        body=html.encode(),
        encoding="utf-8",
    )
    urls = [r.url.split(".uk")[1] for r in spider.parse(response, parent={})]
    assert urls == ["/a/kader/verein/1/plus/1"]
