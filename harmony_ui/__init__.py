import random
import string
import typing
import discord
import traceback

from loguru import logger


async def handle_error(interaction: discord.Interaction, error: Exception) -> typing.NoReturn:
    """
    Handle an exception encountered during an interaction.
    :param interaction: The interaction in which the exception was raised.
    :param error: The raised exception.
    :return: Nothing.
    """
    error_reference = "err_" + "".join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

    if interaction.command:
        logger.warning(f"{error_reference}: "
                       f"An error was raised during interaction with command {interaction.command.name}")
    else:
        logger.warning(f"{error_reference}: An error was raised during interaction with a command.")

    traceback.print_exception(type(error), error, error.__traceback__)

    embed = discord.Embed(
        title="An error occurred",
        description=f"""
        Something went wrong while processing your request.

        Please try again later. If the problem persists, please raise a ticket, citing the following reference:
        `{error_reference}`
        """
    )

    if interaction.response.is_done():
        await interaction.edit_original_response(content=None, embed=embed)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)