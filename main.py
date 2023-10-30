from harmony_config import config  # DO NOT move this import, it'll break the config resolver

import os
import typing
import discord
import harmony_cogs

from loguru import logger
from discord.ext import commands
from harmony_ui.feedback import FeedbackItemView

harmony_management_role_id = config.get_configuration_key(
    "discord.harmony_management_role_id",
    required=True,
    expected_type=int
)


class HarmonyBot(commands.Bot):
    loaded_cogs: typing.List[typing.Type[commands.Cog]] = []
    is_starting_up: bool = True

    def __init__(self) -> typing.NoReturn:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents, command_prefix="$")

    async def setup_hook(self) -> typing.NoReturn:
        self.add_view(FeedbackItemView())

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

        # Load only the cogs that are configured to load on startup.
        startup_cog_names = config.get_configuration_key("cogs.load_on_startup", required=True, expected_type=list)

        for startup_cog_name in startup_cog_names:
            logger.info(f"Automatically loading cog with name {startup_cog_name}.")
            cog_class = harmony_cogs.fetch_cog_by_name(startup_cog_name)

            # note: Calling a class object (cog_class) is the same as calling its constructor
            await self.add_cog(cog_class(self))

            self.loaded_cogs.append(cog_class)

        self.is_starting_up = False


bot = HarmonyBot()


@bot.command()
@commands.guild_only()
@commands.has_role(harmony_management_role_id)
async def sync(
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
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


@bot.command(name="cog")
@commands.guild_only()
@commands.has_role(harmony_management_role_id)
async def manage_cogs(
        ctx: commands.Context,
        operation: typing.Literal["load", "unload", "list"],
        *params: str
) -> typing.NoReturn:
    """
    Command to manage listing, loading and unloading of cogs by a server moderator.
    :param ctx: The command context.
    :param operation: The operation to perform (load, unload, list).
    :param params: The parameters that get passed to each command handler.
    :return: Nothing.
    """
    output_message = ""

    match operation:
        case "load":
            output_message += f"Loaded cogs: **{', '.join(params)}**\n\n"
            for cog_name in params:
                logger.info(f"User {ctx.message.author.name} loaded cog {cog_name}")

                # Does the specified cog even exist?
                try:
                    cog_class = harmony_cogs.fetch_cog_by_name(cog_name)
                except KeyError:
                    output_message += f"- :no_entry_sign: No cog with name `{cog_name}` was found.\n"
                    continue

                # Is the cog already loaded?
                if cog_class in ctx.bot.loaded_cogs:
                    output_message += f"- :no_entry_sign: Cog with name `{cog_name}` is already loaded.\n"
                    continue

                # Try and load the cog
                try:
                    await ctx.bot.add_cog(cog_class(ctx.bot))
                except Exception as e:
                    output_message += (f"- :no_entry_sign: Failed to load `{cog_name}`: "
                                       f"`{type(e).__name__}`: {str(e)}\n")
                    continue

                ctx.bot.loaded_cogs.append(cog_class)
                output_message += f"- :white_check_mark: Loaded `{cog_name}`.\n"
        case "unload":
            output_message += f"Unloaded cogs: **{', '.join(params)}**\n\n"
            for cog_name in params:
                logger.info(f"User {ctx.message.author.name} unloaded cog {cog_name}")

                # Does the specified cog even exist?
                try:
                    cog_class = harmony_cogs.fetch_cog_by_name(cog_name)
                except KeyError:
                    output_message += f"- :no_entry_sign: No cog with name `{cog_name}` was found.\n\n"
                    continue

                # Is the cog even loaded?
                if cog_class not in ctx.bot.loaded_cogs:
                    output_message += f"- :no_entry_sign: Cog with name `{cog_name}` is not loaded.\n"
                    continue

                # Try and unload the cog
                try:
                    await ctx.bot.remove_cog(cog_class.__name__)
                except Exception as e:
                    output_message += (f"- :no_entry_sign: Failed to unload `{cog_name}`: "
                                       f"`{type(e).__name__}`: {str(e)}\n")
                    continue

                ctx.bot.loaded_cogs.remove(cog_class)
                output_message += f"- :white_check_mark: Unloaded `{cog_name}`.\n"
        case "list":
            output_message += "Available cogs:\n\n"

            logger.info(f"User {ctx.message.author.name} listed cogs")

            for cog_name, cog_class in harmony_cogs.get_cog_cache().items():
                is_loaded = "Yes" if cog_class in ctx.bot.loaded_cogs else "No"
                class_name = cog_class.__name__

                output_message += f"- `{cog_name}` (loaded: {is_loaded}, class name: `{class_name}`)\n"
        case _:
            output_message = f"Unknown operation: `{operation}`."

    await ctx.send(output_message, ephemeral=True)

if __name__ == "__main__":
    bot.run(config.get_configuration_key("discord.bot_token", required=True))
