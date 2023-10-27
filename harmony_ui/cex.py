import munch
import typing
import asyncio
import discord
import urllib.parse


class CexSearchResultView(discord.ui.View):
    def __init__(
            self,
            results: typing.List[munch.Munch],
            original_interaction: discord.Interaction,
            original_search_query: str
    ):
        super().__init__(timeout=None)

        self.original_interaction = original_interaction
        self.current_result_index = 0
        self.results_count = len(results)
        self.results = results
        self.previous_result.disabled = True
        self.original_search_query = original_search_query

        if self.results_count == 1:
            self.next_result.disabled = True

        asyncio.get_running_loop().create_task(self.update_result(self.original_interaction))

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple, row=1)
    async def previous_result(self, interaction: discord.Interaction, __: discord.ui.Button):
        self.current_result_index -= 1
        await self.update_result(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple, row=1)
    async def next_result(self, interaction: discord.Interaction, __: discord.ui.Button):
        self.current_result_index += 1
        await self.update_result(interaction)

    async def update_result(self, interaction: discord.Interaction):
        self.previous_result.disabled = (self.current_result_index == 0)
        self.next_result.disabled = (self.current_result_index == self.results_count - 1)

        embed = create_search_result_embed(
            box_item=self.results[self.current_result_index],
            search_query=self.original_search_query,
            current_result_index=self.current_result_index + 1,
            result_count=self.results_count
        )

        if interaction.response.is_done():
            await interaction.edit_original_response(content=None, embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)


def create_search_result_embed(
        box_item: munch.Munch,
        search_query: str,
        current_result_index: int = 0,
        result_count: int = 0,
) -> discord.Embed:
    """
    Convert CeX box item data to a Discord embed.
    :param box_item: The box item to convert, as a Munch.
    :param search_query: The search query to add to the title.
    :param current_result_index: The current result.
    :param result_count: The total number of results.
    :return: The created embed.
    """
    if current_result_index > 0 and result_count > 1:
        title = f'Result {current_result_index} of {result_count} for {search_query}'
    else:
        title = f'Result for {search_query}'

    embed = discord.Embed(
        title=title,
        color=0xff0000,
        url=f"https://uk.webuy.com/product-detail?id={box_item.boxId}"
    )

    embed.set_footer(text="This tool is in beta and might yield unexpected results.")

    parsed_image_url = "https://" + urllib.parse.quote(box_item.imageUrls.medium.replace("https://", ""))
    embed.set_thumbnail(url=parsed_image_url)

    embed.add_field(
        name="Item Name",
        value=box_item.boxName,
        inline=False
    )
    embed.add_field(
        name="Category",
        value=f"{box_item.superCatFriendlyName} - {box_item.categoryFriendlyName}",
        inline=False
    )
    embed.add_field(
        name="In stock online?",
        value="No" if box_item.outOfEcomStock else "Yes",
        inline=False
    )

    embed.add_field(name="WeSell for", value=f"£{box_item.sellPrice}")
    embed.add_field(name="WeBuy for (Cash)", value=f"£{box_item.cashPrice}")
    embed.add_field(name="WeSell for (Voucher)", value=f"£{box_item.exchangePrice}")

    return embed


def create_no_items_found_embed(search_query: str) -> discord.Embed:
    """
    Create the embed shown if no item is found for a given search query.
    :param search_query: The search query.
    :return: The created embed.
    """
    return discord.Embed(
        title=f"No results for {search_query}",
        description="Try refining your search query to yield more results.\n\n"
                    "If you think there should be results, then the bot may have been blocked by CeX."
    )
