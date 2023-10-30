import typing
import discord
import harmony_ui
import harmony_ui.verify

from loguru import logger
from discord import app_commands
from discord.ext import commands
from harmony_config import config
from harmony_services import db as harmony_db
from harmony_scheduled.verify import check_reddit_accounts_task, check_discord_roles_task

configured_verify_role_data = config.get_configuration_key("roles", required=True, expected_type=list)
subreddit_name = config.get_configuration_key("reddit.subreddit_name", required=True)
guild_id = config.get_configuration_key("discord.guild_id", required=True, expected_type=int)
verified_role = discord.Object(
    config.get_configuration_key("discord.verified_role_id", required=True, expected_type=int)
)
user_management_role = discord.Object(
    config.get_configuration_key("discord.harmony_management_role_id", required=True, expected_type=int)
)


class Verify(commands.Cog):
    _cog_name = "verify"

    def __init__(self, bot: commands.Bot) -> typing.NoReturn:
        self.bot = bot

        whois_context_menu = app_commands.ContextMenu(
            name="Whois",
            guild_ids=[guild_id],
            callback=self.display_whois_result
        )

        update_role_context_menu = app_commands.ContextMenu(
            name="Update Role",
            guild_ids=[guild_id],
            callback=self.update_role
        )

        self.bot.tree.add_command(whois_context_menu)
        self.bot.tree.add_command(update_role_context_menu)

        check_reddit_accounts_task.start(self.bot)
        check_discord_roles_task.start(self.bot)

    def cog_unload(self) -> typing.NoReturn:
        check_reddit_accounts_task.cancel()
        check_discord_roles_task.cancel()

    @app_commands.command(
        name='verify',
        description='Link your Reddit and Discord accounts to gain access to member-only benefits.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(guild_id))
    async def display_verification_dialog(self, interaction: discord.Interaction) -> typing.NoReturn:
        """
        Command to display the verification model, to allow users to verify their Reddit accounts.
        :param interaction: The interaction context for this command.
        :return: Nothing.
        """
        try:
            if harmony_db.has_verification_data(interaction.user.id):
                await interaction.response.send_message(
                    "Looks like you're already verified. If you can't access the server, **please raise a ticket.**",
                    ephemeral=True)

                return

            if harmony_db.has_pending_verification(interaction.user.id):
                await interaction.response.send_modal(harmony_ui.verify.EnterVerificationTokenModal())
            else:
                await interaction.response.send_modal(harmony_ui.verify.EnterRedditUsernameModal())
        except Exception as e:
            await harmony_ui.handle_error(interaction, e)

    @app_commands.command(
        name='unverify',
        description='Unlink your Discord and Reddit accounts.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(guild_id))
    async def display_unverify_dialog(self, interaction: discord.Interaction):
        try:
            if harmony_db.has_verification_data(interaction.user.id):
                await interaction.response.send_modal(harmony_ui.verify.UnverifyConfirmationModal())
            elif harmony_db.has_pending_verification(interaction.user.id):
                pending_verification = harmony_db.get_pending_verification(interaction.user.id)
                pending_verification.delete()
                await interaction.response.send_message(
                    "Your pending verification has been cancelled. You can `/verify` again at any time.", ephemeral=True)
            else:
                await interaction.response.send_message("Doesn't look like you're verified.", ephemeral=True)
        except Exception as e:
            await harmony_ui.handle_error(interaction, e)

    @app_commands.command(
        name='whois',
        description='Look up a user to get information about their account.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(guild_id))
    async def whois(self, interaction: discord.Interaction, query: str):
        try:
            # Standardise the format of reddit username lookup
            query = query.replace('/u/', 'u/')

            result = None
            guild_member = None

            if query.startswith("u/"):
                logger.info(f"/whois: {interaction.user.name} looked up user by Reddit username {query}")
                result = harmony_db.get_verification_data(reddit_username=query.replace("u/", ""))
            elif query.isnumeric():
                logger.info(f"/whois: {interaction.user.name} looked up user by Discord user ID {query}")
                result = harmony_db.get_verification_data(discord_user_id=int(query))
            else:
                logger.info(f"/whois: {interaction.user.name} looked up user by Discord username {query}")
                guild_member = discord.utils.get(interaction.guild.members, name=query)

            if not result and not guild_member:
                await interaction.response.send_message(
                    f"No verified user found for the query `{query}`.",
                    ephemeral=True
                )
                return

            if not guild_member:
                guild_member = interaction.guild.get_member(result.discord_user.discord_user_id)

            if not guild_member:
                logger.warning(f"/whois: Discord guild member lookup for ID "
                               f"{result.discord_user.discord_user_id} returned no result")
                raise Exception(f"Failed to lookup Discord user ID {result.discord_user.discord_user_id}")

            await self.display_whois_result(interaction=interaction, member=guild_member)
        except Exception as e:
            await harmony_ui.handle_error(interaction, e)

    @app_commands.checks.has_role(user_management_role)
    async def update_role(self, interaction: discord.Interaction, member: discord.Member):
        try:
            verification_data = harmony_db.get_verification_data(discord_user_id=member.id)

            if not verification_data:
                await interaction.response.send_message(
                    f"**{member.name}** hasn't verified themselves, so their flair can't be updated. "
                    "(I don't know their Reddit username 🙃)", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "## Please select the new role:",
                    view=harmony_ui.verify.UpdateRoleView(target_member=member, original_interaction=interaction),
                    ephemeral=True
                )
        except Exception as e:
            await harmony_ui.handle_error(interaction, e)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            verification_data = harmony_db.get_verification_data(discord_user_id=member.id)

            if verification_data:
                verification_data.delete()
        except Exception as e:
            logger.warning(f"Member {member.name} left the Discord server, but failed to remove their data.")

    async def display_whois_result(self, interaction: discord.Interaction, member: discord.Member):
        verification_data = harmony_db.get_verification_data(discord_user_id=member.id)

        embed = discord.Embed(
            title=f"Whois information for {member.display_name}"
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="Verified Reddit account", value="Yes" if verification_data else "No")

        if verification_data:
            embed.add_field(name="Reddit username", value=verification_data.reddit_user.reddit_username,
                            inline=False)

            embed.add_field(name="Verified since", value=verification_data.user_verification_data.verified_at,
                            inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> typing.NoReturn:
    await bot.add_cog(Verify(bot))
