import typing
import discord
import harmony_services.db
import harmony_ui.feedback

from loguru import logger
from discord import app_commands
from discord.ext import commands
from harmony_config import config


feedback_channel_id = config.get_configuration_key("feedback.feedback_channel_id", required=True, expected_type=int)
discord_guild_id = config.get_configuration_key("discord.guild_id", required=True, expected_type=int)


class Feedback(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.feedback_channel = bot.get_guild(discord_guild_id).get_channel(feedback_channel_id)
        if not self.feedback_channel:
            logger.error(f"Feedback channel with ID {feedback_channel_id} doesn't exist.")
            raise RuntimeError()

    @app_commands.command(
        name='feedback',
        description='Create feedback items for the community to vote on.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(discord_guild_id))
    async def feedback(self, interaction: discord.Interaction) -> typing.NoReturn:
        """
        Method invoked when the user performs the feedback slash command.
        :param interaction: The interaction to use to respond to the user.
        :return: Nothing.
        """
        await interaction.response.send_modal(harmony_ui.feedback.CreateFeedbackItemModal(self.feedback_channel))

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> typing.NoReturn:
        """
        Delete feedback data when the message containing its voting view is deleted.
        :param payload: The data about which message was deleted.
        :return: Nothing.
        """
        logger.info(f"Deleting feedback data because message with ID {payload.message_id} "
                    f"was deleted from #{self.feedback_channel.name}")

        if payload.channel_id == self.feedback_channel.id:
            harmony_services.db.delete_feedback_data(payload.message_id)