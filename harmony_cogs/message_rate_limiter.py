import datetime

import munch
import typing
import discord
import harmony_services.db
import harmony_ui.message_rate_limiter

from loguru import logger
from main import HarmonyBot
from discord.ext import commands
from harmony_config import config

discord_guild_id = config.get_configuration_key("discord.guild_id", required=True, expected_type=int)


class MessageRateLimiter(commands.Cog):
    _cog_name = "message-rate-limiter"

    def __init__(self, bot: HarmonyBot):
        self.bot = bot

        self.limited_channels = munch.munchify(
            config.get_configuration_key(
                "message_rate_limiter.limited_channels",
                required=True,
                expected_type=list
            )
        )

        self.validate_config()

        self.limited_channel_ids = [channel.channel_id for channel in self.limited_channels]

    def validate_config(self):
        for channel in self.limited_channels:
            if not hasattr(channel, "channel_id") or not hasattr(channel, "rate_limit_seconds"):
                raise KeyError(f"Misconfigured channel: {channel} doesn't have channel_id/rate_limit_seconds")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> typing.NoReturn:
        """
        Event fired when a message is sent.
        This handler checks to see when the user last sent a message in a limited channel,
        and restricts them from sending another until the rate limit expires.
        :param message: The message to validate.
        :return: Nothing.
        """
        # If the message isn't in a guild or not in a limited channel, do nothing.
        if not message.guild or message.channel.id not in self.limited_channel_ids:
            return

        # If the message was sent by the bot, do nothing.
        if message.author.id == self.bot.user.id:
            return

        # Get any data about rate limiting in this channel for the user that sent the message.
        rate_limiter_data = harmony_services.db.get_rate_limiter_message_data(message.author.name, message.channel.id)
        channel_limit = [channel for channel in self.limited_channels if channel.channel_id == message.channel.id][0]

        if not rate_limiter_data:
            # If there is no data, then save it and move on.
            logger.info(f"Saving rate limiter data for channel ID {message.channel.id}, author {message.author.name}")
            harmony_services.db.save_rate_limiter_message_data(message.author.name, message.channel.id)
        else:
            # Is the expiry timestamp after the current time in UTC?
            original_message_timestamp = rate_limiter_data.message_timestamp
            expiry_timestamp = original_message_timestamp + datetime.timedelta(seconds=channel_limit.rate_limit_seconds)

            if expiry_timestamp > datetime.datetime.utcnow():
                # If so, then delete the message and notify the author.
                logger.info(f"Deleting {message.author.name}'s message in channel ID {message.channel.id}: "
                            f"their last message (sent at {original_message_timestamp}) is less than "
                            f"{channel_limit.rate_limit_seconds} old.")

                guild_channel = message.guild.get_channel(message.channel.id)

                await message.author.send(embed=harmony_ui.message_rate_limiter.create_message_limited_embed(
                    author_name=message.author.name,
                    guild_name=message.guild.name,
                    guild_channel_name=guild_channel.name,
                    guild_channel_url=guild_channel.jump_url,
                    original_message_timestamp=rate_limiter_data.message_timestamp,
                    rate_limit_seconds=channel_limit.rate_limit_seconds,
                    deleted_message_content=message.clean_content
                ))

                await message.delete()
            else:
                # Delete their existing data and move on.
                rate_limiter_data.delete()
