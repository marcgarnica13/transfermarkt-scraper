from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re
from tfmkt.utils import background_position_in_px_to_minute

class GamesSpider(BaseSpider):
  name = 'games'

  def parse(self, response, parent):
    """Parse competition page. From this page follow to the games and fixutres page.

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns requests 1 1
    @cb_kwargs {"parent": "dummy"}
    @scrapes type href parent
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    cb_kwargs = {
      'base' : {
        'parent': parent
      }
    }

    footer_links = response.css('div.footer-links')
    for footer_link in footer_links:
      text = footer_link.xpath('a//text()').get().strip()
      if text in [
        "All fixtures & results",
        "All games"
        ]:
        next_url = footer_link.xpath('a/@href').get()

        return response.follow(next_url, self.extract_game_urls, cb_kwargs=cb_kwargs)

  def extract_game_urls(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020
    @returns requests 330 390
    @cb_kwargs {"base": {"href": "some_href", "type": "league", "parent": {}}}
    @scrapes type href parent game_id 
    """

    # inspect_response(response, self)
    # exit(1)

    game_links = response.css('a.ergebnis-link')
    # print(len(game_links), "links_found")
    for game_link in game_links:
      href = game_link.xpath('@href').get()

      cb_kwargs = {
        'base': {
          'parent': base['parent'],
          'href': href
        }
      }

      yield response.follow(href, self.parse_game, cb_kwargs=cb_kwargs)


  def extract_game_events(self, response, event_type):
    event_elements = response.xpath(
      f"//div[./h2/@class = 'content-box-headline' and normalize-space(./h2/text()) = '{event_type}']//div[@class='sb-aktion']"
    )

    events = []
    for e in event_elements:
      event = {}
      event["type"] = event_type
      background_position_match = re.match(
        "background-position: ([-+]?[0-9]+)px ([-+]?[0-9]+)px;",
        e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/@style").get()
      )
      event["minute"] = background_position_in_px_to_minute(
        int(background_position_match.group(1)),
        int(background_position_match.group(2)),
      )
      extra_minute_text = self.safe_strip(
        e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/text()").get()
      )
      if len(extra_minute_text) <= 1:
        extra_minute = None
      else:
        extra_minute = int(extra_minute_text)

      event["extra"] = extra_minute
      event["player"] = {
        "href": e.xpath("./div[@class = 'sb-aktion-spielerbild']/a/@href").get()
      }
      event["club"] = {
        "name": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@title").get(),
        "href": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@href").get()
      }

      action_element = e.xpath("./div[@class = 'sb-aktion-aktion']")
      event["action"] = {
        "result": self.safe_strip(
          e.xpath("./div[@class = 'sb-aktion-spielstand']/b/text()").get()
        ),
        "description": self.safe_strip(
          action_element.xpath("./text()").getall()[1]
        ),
        "player_in": {
          "href": action_element.xpath(".//div/a/@href").get()
        }
      }
      events.append(event)

    return events

  def parse_game(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/spielbericht/index/spielbericht/3098550
    @returns items 1 1
    @cb_kwargs {"base": {"href": "some_href/3", "type": "league", "parent": {}}}
    @scrapes type href parent game_id result matchday date stadium attendance home_manager away_manager
    """

    # inspect_response(response, self)
    # exit(1)

    game_id = int(base['href'].split('/')[-1])

    game_box = response.css('div.box-content')

    # extract home and away "boxes" attributes
    home_club_box = game_box.css('div.sb-heim')
    away_club_box = game_box.css('div.sb-gast')

    home_club_href = home_club_box.css('a::attr(href)').get()
    away_club_href = away_club_box.css('a::attr(href)').get()

    home_club_position = home_club_box[0].xpath('p/text()').get()
    away_club_position = away_club_box[0].xpath('p/text()').get()

    formations = response.css('div.aufstellung-unterueberschrift')
    if len(formations) > 0:
      home_club_formation = response.css('div.aufstellung-unterueberschrift')[0].xpath('text()').get().strip('\n').strip('\t')
      away_club_formation = "NAN"
    if len(formations) > 1:
      away_club_formation = response.css('div.aufstellung-unterueberschrift')[1].xpath('text()').get().strip('\n').strip('\t')
    else:
      home_club_formation = "NAN"
      away_club_formation = "NAN"

    # extract date and time "box" attributes
    datetime_box = game_box.css('div.sb-spieldaten')[0]

    text_elements = [
      element for element in datetime_box.xpath('p//text()') 
      if len(self.safe_strip(element.get())) > 0
    ]

    matchday = self.safe_strip(text_elements[0].get()).split("  ")[0]
    date = self.safe_strip(datetime_box.xpath('p/a[contains(@href, "datum")]/text()').get())
    
    # extract venue "box" attributes
    venue_box = game_box.css('p.sb-zusatzinfos')

    stadium = self.safe_strip(venue_box.xpath('node()')[1].xpath('a/text()').get())
    attendance = self.safe_strip(venue_box.xpath('node()')[1].xpath('strong/text()').get())
    referee = self.safe_strip(venue_box.xpath('a[contains(@href, "schiedsrichter")]/@title').get())

    # extract results "box" attributes
    result_box = game_box.css('div.ergebnis-wrap')

    result = self.safe_strip(result_box.css('div.sb-endstand::text').get())

    # extract from line-ups "box"
    manager_names = response.xpath(
        "//tr[(contains(td/b/text(),'Manager')) or (contains(td/div/text(),'Manager'))]/td[2]/a/text()"
      ).getall()

    game_events = (
      self.extract_game_events(response, event_type="Goals") +
      self.extract_game_events(response, event_type="Substitutions")
    )

    item = {
      **base,
      'type': 'game',
      'game_id': game_id,
      'home_club': {
        'type': 'club',
        'href': home_club_href
      },
      'home_club_position': home_club_position,
      'away_club': {
        'type': 'club',
        'href': away_club_href
      },
      'away_club_position': away_club_position,
      'home_formation': home_club_formation,
      'away_formation': away_club_formation,
      'result': result,
      'matchday': matchday,
      'date': date,
      'stadium': stadium,
      'attendance': attendance,
      'referee': referee,
      'events': game_events
    }

    if len(manager_names) == 2:
      home_manager_name, away_manager_name = manager_names
      item["home_manager"] = {
        'name': home_manager_name
      }
      item["away_manager"] = {
        'name': away_manager_name
      }
    lineup_href = base['href'].replace('index', 'aufstellung')

    cb_kwargs = {
      'base': {
        'main': item,
      }
    }

    yield response.follow(lineup_href, self.parse_game_lineup, cb_kwargs=cb_kwargs)

  def parse_game_lineup(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/spielbericht/aufstellung/spielbericht/3098550
    @returns items 1 1
    @cb_kwargs {"base": {"main": "current game information"}}
    @scrapes type href parent game_id result matchday date stadium attendance home_manager away_manager
    """
    # parsing line up in the other page, for the 4 positions line up
    # response.css('div.table-footer')[0].xpath('table')[0].xpath('tr//td//text()')[2].get()
    footer_boxes = response.css('div.table-footer')
    lineup_item = {}
    for box in footer_boxes:
      box_text_values = box.xpath('tr//td//text()')
      for text_value in box_text_values:
        text_value = box_text_values.get()
        text_value = text_value.replace(" ", "")
        value_key, value = text_value.split(":")
        lineup_item[value_key] = value
    
    # parsing each component of the lineup
    # for 4 different sb-formation and 1,3,5 position.
    # response.css('div.row, sb-formation')[0].xpath('.//table[@class="inline-table"]//tr')[1].xpath('td//text()')[0].get()
    # response.css('div.responsive-table')[3].xpath('.//table[@class="inline-table"]//tr[2]//td//text()').extract()
    player_boxes = response.css('div.responsive-table')
    player_boxes_layout = ["home_team", "away_team", "home_bench", "away_bench"]
    extended_lineup = {}
    lineup_players = []
    for p_i, p_box in enumerate(player_boxes[:4]):
      player_name = p_box.xpath('.//table[@class="inline-table"]//tr[1]//td[2]//a/text()').extract()
      player_hrefs = p_box.xpath('.//table[@class="inline-table"]//tr[1]//td[2]//a/@href').extract()
      print(f"{player_name}: {player_hrefs}")
      position_information_raw = p_box.xpath('.//table[@class="inline-table"]//tr[2]//td//text()').extract()
      for player_i, raw_value in enumerate(position_information_raw):
        raw_value = raw_value.replace(" ", "")
        cut_player_ref = player_hrefs[player_i].split("/saison")[0].replace('leistungsdatendetails', 'profil')
        if "," in raw_value:
          position_key, mv_value = raw_value.split(",")
          extended_lineup.setdefault(
            player_boxes_layout[p_i], {}
          ).setdefault(
            position_key, []
          ).append(mv_value)
          lineup_players.append({"player_name": player_name[player_i], "link": cut_player_ref, "position": position_key, "market_value": mv_value})

    lineup_item["positions"] = extended_lineup
    lineup_item["players"] = lineup_players

    item = {
      **base,
      "lineup": lineup_item
    }

    yield item
 