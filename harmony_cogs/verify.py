import json
import discord
import prawcore.exceptions

import harmony_ui
import harmony_ui.verify

from discord import app_commands
from discord.ext import commands, tasks
from harmony_services import db as harmony_db
from harmony_services import reddit as harmony_reddit
from loguru import logger

with open("config.json", "r") as f:
    config = json.load(f)

configured_verify_role_data = config["roles"]
verified_role = discord.Object(config["discord"]["verified_role_id"])
user_management_role = discord.Object(config["discord"]["harmony_management_role_id"])
subreddit_name = config["reddit"]["subreddit_name"]


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        whois_context_menu = app_commands.ContextMenu(
            name="Whois",
            guild_ids=[int(config["discord"]["guild_id"])],
            callback=self.display_whois_result
        )

        update_role_context_menu = app_commands.ContextMenu(
            name="Update Role",
            guild_ids=[int(config["discord"]["guild_id"])],
            callback=self.update_role
        )

        self.bot.tree.add_command(whois_context_menu)
        self.bot.tree.add_command(update_role_context_menu)

        self.check_reddit_accounts.start()

    def cog_unload(self) -> None:
        self.check_reddit_accounts.cancel()

    @app_commands.command(
        name='verify',
        description='Link your Reddit and Discord accounts to gain access to member-only benefits.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(int(config["discord"]["guild_id"])))
    async def display_verification_dialog(self, interaction: discord.Interaction) -> None:
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
    @app_commands.guilds(discord.Object(int(config["discord"]["guild_id"])))
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
    @app_commands.guilds(discord.Object(int(config["discord"]["guild_id"])))
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

    @app_commands.checks.has_role(config["discord"]["harmony_management_role_id"])
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

    @tasks.loop(seconds=config["schedule"]["reddit_account_check_interval_seconds"])
    async def check_reddit_accounts(self):
        """
        Check Reddit accounts to make sure they haven't been banned from the subreddit, or deleted their account.
        :return: Nothing.
        """
        job_enabled: bool = config["schedule"]["reddit_account_check_enabled"]

        if not job_enabled:
            logger.info("Scheduled Reddit account check is disabled.")
            return

        reporting_channel = None
        removed_users = []
        dry_run: bool = config["schedule"]["reddit_account_check_dry_run"]
        bans_fetch_limit: int = config["schedule"]["reddit_account_check_ban_fetch_limit"]

        try:
            guild = await self.bot.fetch_guild(int(config["discord"]["guild_id"]))

            if not guild:
                raise Exception(f"Failed to fetch the guild with ID {config['discord']['guild_id']}.")

            reporting_channel = await guild.fetch_channel(
                config["schedule"]["reddit_account_check_reporting_channel_id"]
            )

            if not reporting_channel:
                raise Exception(f"Failed to fetch the reporting channel with ID "
                                f"{config['schedule']['reddit_account_check_reporting_channel_id']}.")

            if not isinstance(reporting_channel, discord.TextChannel):
                raise Exception(f"Reporting channel is not a TextChannel, ID: "
                                f"{config['schedule']['reddit_account_check_reporting_channel_id']}.")

            logger.info("Running scheduled job to cleanup banned/missing Reddit users")

            users = harmony_db.get_all_verification_data()

            logger.info(f"Fetching bans from r/{subreddit_name}, limit={bans_fetch_limit}")
            subreddit_bans = [redditor.name for redditor in harmony_reddit.subreddit_bans(subreddit_name, limit=bans_fetch_limit)]

            logger.info(f"Done - got {len(subreddit_bans)} bans.")

            for user in users:
                reddit_username = user.reddit_user.reddit_username
                try:
                    member = await guild.fetch_member(user.discord_user.discord_user_id)
                except discord.errors.NotFound:
                    logger.info(f"Redditor u/{reddit_username} is no longer in the Discord server, cleaning up data.")

                    if not dry_run:
                        user.delete()

                    continue

                try:
                    reddit_user_exists = harmony_reddit.reddit_user_exists(reddit_username)
                    reddit_account_suspended = harmony_reddit.redditor_suspended(reddit_username)
                    reddit_account_sub_banned = reddit_username in subreddit_bans
                except prawcore.exceptions.TooManyRequests:
                    logger.warning(f"Hit Reddit rate limit while processing member {member.name}, ignoring for now.")
                    continue

                if not reddit_user_exists:
                    logger.info(f"Member {member.name}'s Reddit account no longer exists: u/{reddit_username}")
                    removed_users.append(reddit_username)

                    if not dry_run:
                        await member.remove_roles(verified_role, reason="User's Reddit account no longer exists.")
                        try:
                            await member.send(
                                embed=harmony_ui.verify.create_nonexistent_reddit_account_embed(
                                    reddit_username,
                                    guild.name
                                )
                            )
                        except Exception:
                            logger.warning(f"Failed to notify {member.name} "
                                           f"that their Reddit account u/{reddit_username} doesn't exist.")

                        user.delete()
                    continue

                if reddit_account_suspended:
                    logger.info(f"Member {member.name}'s Reddit account is suspended: u/{reddit_username}")
                    removed_users.append(reddit_username)

                    if not dry_run:
                        await member.remove_roles(verified_role, reason="User's Reddit account is suspended.")
                        try:
                            await member.send(
                                embed=harmony_ui.verify.create_suspended_reddit_account_embed(
                                    reddit_username,
                                    guild.name
                                )
                            )
                        except Exception:
                            logger.warning(f"Failed to notify {member.name} "
                                           f"that their Reddit account u/{reddit_username} is suspended.")

                        user.delete()
                    continue

                if reddit_account_sub_banned:
                    logger.info(f"Member {member.name}'s Reddit account (u/{reddit_username}) "
                                f"is banned from r/{subreddit_name}")
                    removed_users.append(reddit_username)
                    if not dry_run:
                        try:
                            await member.send(
                                embed=harmony_ui.verify.create_banned_reddit_account_embed(
                                    reddit_username,
                                    guild.name,
                                    subreddit_name
                                )
                            )
                        except Exception:
                            logger.warning(f"Failed to notify {member.name} "
                                           f"that their Reddit account u/{reddit_username} "
                                           f"is banned from r/{subreddit_name}.")

                        await member.ban(reason=f"Linked reddit account u/{reddit_username} "
                                                f"is banned from r/{subreddit_name}")

                        user.delete()
                    continue

            report_message = f"All verified Reddit users checked. "

            if removed_users:
                report_message += f"{len(removed_users)} users were processed:\n\n"

                for removed_user in removed_users:
                    report_message += f"- **u/{removed_user}**\n"
            else:
                report_message += "No users were processed."

            if dry_run:
                report_message += "\n\n:information_source: No action has been taken because the dry run flag is set."

            await reporting_channel.send(content=report_message)

        except Exception as e:
            logger.error(f"Something went wrong while running the Reddit accounts ban check job.")

            if reporting_channel and isinstance(reporting_channel, discord.TextChannel):
                await reporting_channel.send(content="## Something went wrong when checking Reddit users!\n\n"
                                               "Please check the bot logs for more details.")

            raise e

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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verify(bot))
