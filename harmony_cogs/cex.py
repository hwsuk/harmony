import json
import httpx
import munch
import typing
import urllib
import discord
import harmony_ui
import harmony_ui.cex

from loguru import logger
from discord import app_commands
from discord.ext import commands
from harmony_config import config


class CexSearch(commands.Cog):
    base_url = "https://wss2.cex.uk.webuy.io/v3/boxes?q=$_SEARCH_QUERY&firstRecord=1&count=50&sortOrder=desc"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        try:
            self.proxy_url = config.get_configuration_key("cex.http_proxy_url")
        except KeyError:
            logger.warning("No HTTP proxy is configured for the CeX searches.")
            self.proxy_url = None

    @app_commands.command(
        name='cex',
        description='Search CeX UK listings to get an idea of how to price your items.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(
        config.get_configuration_key("discord.guild_id", required=True, expected_type=int)))
    async def cex_search(self, interaction: discord.Interaction, search_query: str) -> typing.NoReturn:
        """
        Method invoked when the user performs the CeX search slash command.
        :param interaction: The interaction to use to send messages.
        :param search_query: The query to use when searching CeX.
        :return: Nothing.
        """
        logger.info(f"{interaction.user.name} searched CeX with query '{search_query}'")

        await interaction.response.send_message(
            f":mag: Searching CeX for **{search_query}**...",
            ephemeral=True
        )

        try:
            response = await self.fetch_cex_items(search_query)
            items = await self.parse_cex_response(response)

            if items:
                await interaction.edit_original_response(
                    content=None,
                    view=harmony_ui.cex.CexSearchResultView(
                        results=items,
                        original_interaction=interaction,
                        original_search_query=search_query
                    )
                )
            else:
                await interaction.edit_original_response(
                    content=None,
                    embed=harmony_ui.cex.create_no_items_found_embed(search_query)
                )
        except Exception as e:
            await harmony_ui.handle_error(interaction, e)

    async def fetch_cex_items(self, search_query: str) -> munch.Munch:
        """
        Fetch the item data from CeX API endpoint.
        :param search_query: The query to use when searching for items.
        :return: The data returned from the API.
        """
        formatted_url = self.base_url.replace("$_SEARCH_QUERY", self.urlencode_search_query(search_query))

        async with httpx.AsyncClient(proxies=self.proxy_url) as http_client:
            response = await http_client.get(formatted_url)
            return munch.munchify(response.json())

    async def parse_cex_response(self, response_data: munch.Munch) -> typing.List[munch.Munch]:
        """
        Parse the response from CeX API into a list of items.
        :param response_data: The response received from CeX API.
        :return: The list of items, as a list of Munches.
        """
        if not hasattr(response_data, 'response') \
                or not hasattr(response_data.response, 'data') \
                or not hasattr(response_data.response.data, 'boxes'):
            logger.info("Empty/invalid response received from CeX API for specified query.")
            return []

        return response_data.response.data.boxes

    def urlencode_search_query(self, query: str) -> str:
        """
        URL-encode the search query so that it's safe to include in the CeX API URL.
        :param query: The search query to URL-encode.
        :return: The URL-encoded search query.
        """
        return urllib.parse.quote(query)
