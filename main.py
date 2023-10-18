import json
import typing

import discord
from discord.ext import commands
from loguru import logger

from harmony_cogs.verify import Verify

with open('config.json', 'r') as f:
    config = json.load(f)

TEST_GUILD = discord.Object(config["discord"]["guild_id"])


class HarmonyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents, command_prefix="$")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

        await self.add_cog(Verify(self))


bot = HarmonyBot()


@bot.command()
@commands.guild_only()
@commands.has_role(config["discord"]["harmony_management_role_id"])
async def sync(
        ctx: discord.ext.commands.Context,
        guilds: discord.ext.commands.Greedy[discord.Object],
        spec: typing.Optional[typing.Literal["guild", "global", "force_guild"]] = None
) -> None:
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
