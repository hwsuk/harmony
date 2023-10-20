import bs4
import json
import httpx
import discord
import statistics
import urllib.parse
import harmony_ui.ebay
import harmony_models.ebay

from loguru import logger
from discord import app_commands
from discord.ext import commands

with open("config.json", "r") as f:
    config = json.load(f)


class Ebay(commands.Cog):

    base_url = "https://www.ebay.co.uk/sch/i.html?_from=R40&_nkw=$_SEARCH_QUERY" \
               "&_in_kw=4&_ex_kw=&_sacat=0&LH_Sold=1&_udlo=&_udhi=&LH_ItemCondition=4&_samilow=&_samihi=" \
               "&_stpos=M300AA&_sargn=-1%26saslc%3D1&_fsradio2=%26LH_LocatedIn%3D1&_salic=3&LH_SubLocation=1" \
               "&_sop=12&_dmd=1&_ipg=60&LH_Complete=1&rt=nc&LH_PrefLoc=1"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name='ebay',
        description='Search recently-completed eBay listings to get an idea of how to price your items.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(int(config["discord"]["guild_id"])))
    async def ebay(self, interaction: discord.Interaction, search_query: str) -> None:
        """
        Method invoked when the user performs the eBay search slash command.
        :param interaction: The interaction to use to send messages.
        :param search_query: The query to use when searching eBay.
        :return: Nothing.
        """
        logger.info(f"{interaction.user.name} searched eBay with query '{search_query}'")

        try:
            html = await self.fetch_website_data(search_query)
            parse_result = await self.parse_website_data(html)

            if parse_result.trimmed_price_list:
                result_stats = self.calculate_result_averages(parse_result)

                await interaction.response.send_message(
                    embed=harmony_ui.ebay.create_items_found_embed(
                        search_query,
                        parse_result,
                        result_stats
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=harmony_ui.ebay.create_no_items_found_embed(search_query),
                    ephemeral=True
                )
        except Exception as e:
            await harmony_ui.handle_error(interaction, e)

    async def fetch_website_data(self, query: str) -> str:
        """
        Fetch the data from eBay using the public-facing website.
        :param query: The search query to fetch.
        :return: The fetched data from the base_url.
        """
        formatted_url = self.base_url.replace("$_SEARCH_QUERY", self.urlencode_search_query(query))

        # TODO: Configure a proxy for this.
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(formatted_url)
            return response.text

    async def parse_website_data(self, html: str) -> harmony_models.ebay.ParseResult:
        """
        Parse a response from eBay's public-facing website.
        :param html: The HTML fetched from eBay.
        :return: Nothing.
        """
        soup = bs4.BeautifulSoup(html, 'html.parser')

        prices = []
        results = soup.find('div', {'class': 'srp-river-results clearfix'}) \
            .find_all('li', {'class': 's-item s-item__pl-on-bottom'})

        for item in results:
            price = item.find('span', class_='s-item__price').text.replace('£', '').replace(',', '')

            # Removing the results that show a range of prices for the same (sold) listing
            # For example, £169.99 to £189.99 does not show the exact sold price
            if 'to' not in price:
                price = float(price)
                prices.append(price)

        original_prices_count = len(prices)

        # Results must be trimmed as some outliers may exist in the list of sold prices from the search results
        # The results are trimmed from both ends of the list once the data has been sorted from low to high
        trim_percentage = 0.15
        trim_count = original_prices_count * trim_percentage
        trim_count = round(trim_count)

        prices.sort()
        trimmed_prices = prices[trim_count:-trim_count]

        return harmony_models.ebay.ParseResult(
            trimmed_prices,
            trim_percentage,
            trim_count,
            original_prices_count
        )

    def calculate_result_averages(self, results: harmony_models.ebay.ParseResult) -> harmony_models.ebay.ResultStatistics:
        """
        Calculate the mean, median and mode prices for a set of parsed items.
        :param results: The results object returned from parse_website_data.
        :return: The result averages.
        """
        trimmed_mean = statistics.mean(results.trimmed_price_list)
        median = statistics.median(results.trimmed_price_list)
        mode = statistics.mode(results.trimmed_price_list)
        min_value = min(results.trimmed_price_list)
        max_value = max(results.trimmed_price_list)

        return harmony_models.ebay.ResultStatistics(
            trimmed_mean,
            median,
            mode,
            min_value,
            max_value
        )

    def urlencode_search_query(self, query: str) -> str:
        """
        URL-encode the search query so that it's safe to include in the eBay scrape URL.
        :param query: The search query to URL-encode.
        :return: The URL-encoded search query.
        """
        return urllib.parse.quote(query)
