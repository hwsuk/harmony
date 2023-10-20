import json
import discord

import harmony_models.ebay

with open("config.json", "r") as f:
    config = json.load(f)


def create_no_items_found_embed(search_query: str) -> discord.Embed:
    """
    Create an embed to be displayed when no results are returned from an eBay search.
    :param search_query: The originally entered search query.
    :return: The embed.
    """
    embed = discord.Embed(
        title=f'No results for {search_query}',
        color=0xce2d32
    )

    embed.add_field(name='Wrong spelling?',
                    value=f'Make sure you spelt your query correctly, as the search filter is '
                          f'looking for an exact match. Your search term `{search_query}` may be '
                          f'spelt incorrectly.\n\n',
                    inline=False)

    embed.add_field(name='No used items being sold with your search query',
                    value=f'There may be no items recently sold for your search terms. '
                          f'on eBay. Try experimenting with the wording of your query.\n\n'
                          f'**Search filters in use**: Exact words, Sold listings, Used, UK only',
                    inline=False)

    embed.add_field(name='Bot has been blocked',
                    value=f'If you know that items for your search query were sold recently, '
                          f'and spelling is correct, then the bot may have been IP blocked by '
                          f'eBay.\n\n'
                          f'In this case, it might be better for you to use the '
                          f'[eBay Advanced search](https://www.ebay.co.uk/sch/ebayadvsearch)'
                          f' to manually search for your item.',
                    inline=False)

    return embed


def create_items_found_embed(
        search_query: str,
        parsed_result: harmony_models.ebay.ParseResult,
        result_stats: harmony_models.ebay.ResultStatistics
) -> discord.Embed:
    """
    Create an embed to be displayed when results are returned from an eBay search.
    :param search_query: The originally entered search query.
    :param parsed_result: The parsed results from eBay.
    :param result_stats: The calculated result statistics.
    :return: The embed.
    """

    embed = discord.Embed(
        title=f'Results for eBay search: {search_query}',
        description=f'Note: These values are intended to give you an idea of how to price your items, '
                    f'but due to the limitations of eBay search, may not be entirely accurate.',
        color=0x6b9312
    )

    embed.add_field(name='Average Sold Price', value=f'£{result_stats.trimmed_mean:.2f}', inline=False)
    embed.add_field(name='Median', value=f'£{result_stats.median:.2f}', inline=True)
    embed.add_field(name='Mode', value=f'£{result_stats.mode:.2f}', inline=True)
    embed.add_field(
        name='Range',
        value=f'£{result_stats.min_price:.2f} to £{result_stats.max_price:.2f}',
        inline=True
    )

    embed.set_thumbnail(
        url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/EBay_logo.svg/2560px-EBay_logo.svg.png'
    )

    embed.set_footer(
        text=f'There were a total of {parsed_result.original_prices_count} search results. '
             f'After trimming {parsed_result.trim_count * 2} results, '
             f'there were {len(parsed_result.trimmed_price_list)} left.',
        icon_url='https://img.icons8.com/fluency/512/paid.png'
    )

    return embed