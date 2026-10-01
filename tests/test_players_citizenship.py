"""Citizenship extraction on player profile pages (players + players_from_file spiders).

Run with: poetry run python -m unittest discover -s tests -t . -v
"""
import os
import re
import unittest

from scrapy.http import HtmlResponse, Request

from tfmkt.spiders.players import PlayersSpider
from tfmkt.spiders.players_from_file import PlayersFromFileSpider

SAMPLES = os.path.join(os.path.dirname(__file__), '..', 'samples', 'html')
BASE_URL = 'https://www.transfermarkt.com'


def read_sample(name):
  with open(os.path.join(SAMPLES, name), 'r', encoding='utf-8') as f:
    return f.read()


def make_response(html, href):
  url = BASE_URL + href
  return HtmlResponse(url=url, body=html.encode('utf-8'), encoding='utf-8', request=Request(url=url))


def remove_citizenship(html):
  """Drop the 'Citizenship:' label and its value span from a profile page."""
  stripped, n = re.subn(
    r'<span[^>]*>Citizenship:</span>\s*<span[^>]*>.*?</span>', '', html, flags=re.DOTALL
  )
  assert n >= 1, 'fixture has no Citizenship row to remove'
  return stripped


def scraped_attributes(spider, response, href):
  """Run the profile parser and return the attributes handed to the national career request."""
  base = {'type': 'player', 'href': href, 'parent': {}}
  if isinstance(spider, PlayersFromFileSpider):
    results = list(spider.parse(response, parent=base))
  else:
    results = list(spider.parse_details(response, base=base))
  assert len(results) == 1
  return results[0].cb_kwargs['attributes']


def blank_flag_titles(html):
  """Blank out every flag title in the 'Citizenship:' value span."""
  def blank(match):
    return re.sub(r'title="[^"]*"', 'title=" "', match.group(0))
  stripped, n = re.subn(
    r'<span[^>]*>Citizenship:</span>\s*<span[^>]*>.*?</span>', blank, html, flags=re.DOTALL
  )
  assert n >= 1, 'fixture has no Citizenship row to blank'
  return stripped


CASES = [
  # (label, fixture html loader, href, expected citizenship)
  # diego_costa.html: live profile fetched 2026-10-01, page lists Spain then Brazil
  ('dual', lambda: read_sample('diego_costa.html'), '/diego-costa/profil/spieler/44779', ['Spain', 'Brazil']),
  ('single', lambda: read_sample('casado.html'), '/marc-casado/profil/spieler/576024', ['Spain']),
  # heung_min_son.html: live profile fetched 2026-10-01, a comma inside a country name stays one element
  ('comma in name', lambda: read_sample('heung_min_son.html'), '/heung-min-son/profil/spieler/91845', ['Korea, South']),
  ('missing', lambda: remove_citizenship(read_sample('diego_costa.html')), '/diego-costa/profil/spieler/44779', None),
  ('blank titles', lambda: blank_flag_titles(read_sample('diego_costa.html')), '/diego-costa/profil/spieler/44779', None),
]


class CitizenshipTest(unittest.TestCase):

  def _check(self, spider_cls):
    # empty parents file, so spider init neither reads stdin nor scrapes for entrypoints
    spider = spider_cls(parents=os.devnull)
    for label, load_html, href, expected in CASES:
      with self.subTest(case=label):
        attributes = scraped_attributes(spider, make_response(load_html(), href), href)
        self.assertEqual(attributes['citizenship'], expected)

  def test_players_spider(self):
    self._check(PlayersSpider)

  def test_players_from_file_spider(self):
    self._check(PlayersFromFileSpider)


if __name__ == '__main__':
  unittest.main()
