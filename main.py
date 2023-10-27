import os
import json
import typing
import discord
import harmony_ui.feedback

from loguru import logger
from discord.ext import commands
from harmony_cogs.ebay import Ebay
from harmony_cogs.verify import Verify
from harmony_cogs.cex import CexSearch
from harmony_cogs.feedback import Feedback

with open('config.json', 'r') as f:
    config = json.load(f)


class HarmonyBot(commands.Bot):
    def __init__(self) -> typing.NoReturn:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents, command_prefix="$")

    async def setup_hook(self) -> typing.NoReturn:
        self.add_view(harmony_ui.feedback.FeedbackItemView())

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

        app_version = os.getenv("HARMONY_APP_VERSION")

        if app_version:
            await self.change_presence(
                activity=discord.Game(
                    name=f"Harmony v{app_version}, at your service.",
                )
            )

        await self.add_cog(Verify(self))
        await self.add_cog(Ebay(self))
        await self.add_cog(CexSearch(self))
        await self.add_cog(Feedback(self))


bot = HarmonyBot()


@bot.command()
@commands.guild_only()
@commands.has_role(config["discord"]["harmony_management_role_id"])
async def sync(
        ctx: discord.ext.commands.Context,
        guilds: discord.ext.commands.Greedy[discord.Object],
        spec: typing.Optional[typing.Literal["guild", "global", "force_guild"]] = None
) -> typing.NoReturn:
    """
    Command to update the slash commands either globally, on the current guild, or on a specified set of guilds.
    :param ctx: The command context.
    :param guilds: The guilds to update (optional).
    :param spec: The type of update to execute.
    :return:
    """
    if not guilds:
        if spec == "guild":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "global":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "force_guild":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the guild.'}"
        )

        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


bot.run(config["discord"]["bot_token"])
