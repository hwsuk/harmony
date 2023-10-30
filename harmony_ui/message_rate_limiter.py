import discord
import datetime


def create_message_limited_embed(
        author_name: str,
        guild_name: str,
        guild_channel_name: str,
        guild_channel_url: str,
        original_message_timestamp: datetime.datetime,
        rate_limit_seconds: int,
        deleted_message_content: str
) -> discord.Embed:
    """
    Create the embed sent to a member when their message is rate-limited.
    :param author_name: The name of the author.
    :param guild_name: The name of the guild in which the message was rate-limited.
    :param guild_channel_name: The name of the channel in which the message was rate-limited.
    :param guild_channel_url: The URL of the channel in which the message was rate-limited.
    :param original_message_timestamp: The timestamp of the original message.
    :param rate_limit_seconds: The rate limit that was enforced.
    :param deleted_message_content: The content of the original message.
    :return: The embed sent to a member when their message is rate-limited.
    """
    expiry_timestamp = original_message_timestamp + datetime.timedelta(seconds=rate_limit_seconds)

    embed_description = f"""
    Hi {author_name},
    
    Your message in [{guild_name}'s #{guild_channel_name} channel]({guild_channel_url}) was deleted because your most recent message was sent too soon.
    
    You need to wait until at least <t:{int(expiry_timestamp.timestamp())}:F> to send your next message.
    """

    if len(deleted_message_content) < 1200:
        embed_description += (f"\nFor your own reference, the message you just sent said:\n\n"
                              f"```\n"
                              f"{deleted_message_content}\n"
                              f"```")

    return discord.Embed(
        title=f"Your message in {guild_name} was deleted",
        description=embed_description,
        color=0xfc0000
    )
