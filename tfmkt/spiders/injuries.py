from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response
import re


class InjuriesSpider(BaseSpider):
    name = "injuries"

    def parse(self, response, parent):
        """
        Parse injuries page. From a player main page it jumps into injuries information
        and extracts all the information from the players injuries

        @url https://www.transfermarkt.co.uk/paul-delecroix/profil/spieler/81543
        @returns requests 1 1
        @cb_kwargs {"parent": "dummy"}
        @scrapes type href parent
        """

        # uncommenting the two lines below will open a scrapy shell with the context of this request
        # when you run the crawler. this is useful for developing new extractors

        # inspect_response(response, self)
        # exit(1)

        cb_kwargs = {"base": {"parent": parent}}
        injuries_link = parent["href"].replace("profil", "verletzungen")
        return response.follow(
            injuries_link, self.extract_injuries_info, cb_kwargs=cb_kwargs
        )

    def extract_injuries_info(self, response, base):
        """
        Parse injuries page. From a player main page it jumps into injuries information
        and extracts all the information from the players injuries

        @url https://www.transfermarkt.co.uk/paul-delecroix/verletzungen/spieler/81543
        @returns requests 1 1
        @cb_kwargs {"parent": "dummy"}
        @scrapes type href parent
        """
        # Get full table
        print("extract")
        # By row push new objects
        injury_navigations = response.css("a.tm-pagination__link")
        injury_links = []
        for navigation in injury_navigations:
            injury_href = navigation.xpath("@href").get()
            if injury_href not in injury_links:
                injury_links.append(injury_href)
                cb_kwargs = {"base": {"parent": base["parent"], "href": injury_href}}
                yield response.follow(
                    injury_href, self.parse_injury_table, cb_kwargs=cb_kwargs
                )
        if len(injury_navigations) == 0:
            yield response.follow(
                response.request.url,
                self.parse_injury_table,
                cb_kwargs={
                    "base": {"parent": base["parent"], "href": response.request.url}
                },
            )

    def parse_injury_table(self, response, base):
        """
        Parse injuries page. From a player main page it jumps into injuries information
        and extracts all the information from the players injuries

        @url https://www.transfermarkt.co.uk/paul-delecroix/verletzungen/spieler/81543
        @returns requests 1 1
        @cb_kwargs {"parent": "dummy"}
        @scrapes type href parent


        inspect_response(response, self)
        exit(1)
        """
        print("parse")

        injury_table_rows = response.xpath('//div[@id="yw1"]/table//tbody/tr')
        # headers = ['season', 'injury', 'from', 'until', 'days', 'games_missed']
        for table_row in injury_table_rows:
            injury_array = table_row.xpath("td/text()").extract()
            flags_zone = table_row.xpath(
                'td[@class="rechts hauptlink wappen_verletzung"]/a'
            )
            player_team = None
            player_national_team = None
            if len(flags_zone) > 0:
                player_team = flags_zone[0].xpath("img/@alt").get()
            if len(flags_zone) > 1:
                player_national_team = flags_zone[1].xpath("img/@alt").get()
            injury = {
                "season": injury_array[0],
                "injury": injury_array[1],
                "from": injury_array[2],
                "until": injury_array[3],
                "days": injury_array[4],
                "team": player_team or "Unknown",
                "national_team": player_national_team or "Unknown",
            }

            item = {**base, "type": "injury", "injury": injury}
            yield item
