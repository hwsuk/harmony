import json
import random
import re
import string
import traceback

import discord

from discord import app_commands
from discord.ext import commands
from loguru import logger

from harmony_models import verify as verify_models
from harmony_services import db as harmony_db
from harmony_services import reddit as harmony_reddit

with open("config.json", "r") as f:
    config = json.load(f)

verified_role = discord.Object(config["discord"]["verified_role_id"])


class RedditUsernameField(discord.ui.TextInput):
    def __init__(self):
        super().__init__(
            label='Please enter your Reddit username.',
            placeholder='u/username',
            required=True
        )


class VerificationTokenField(discord.ui.TextInput):
    def __init__(self):
        super().__init__(
            label='Please enter your verification code.',
            placeholder='hwsuk_',
            required=True
        )


class EnterRedditUsernameModal(discord.ui.Modal, title='Verify your Reddit account'):
    reddit_username_field = RedditUsernameField()

    @staticmethod
    def generate_verification_code(prefix: str = "") -> str:
        chars = string.digits + string.ascii_letters
        code = ''.join(random.choice(chars) for _ in range(12))

        return f"{prefix}{code}"

    async def send_verification_code(self, interaction: discord.Interaction) -> None:
        # Is the username even valid?
        username = self.reddit_username_field.value

        if username.startswith('u/'):
            username = username.replace('u/', '')

        # Check if the username is alphanumeric with dashes/underscores.
        username_regex = re.compile(r'^([A-Za-z0-9_-])+$')

        if not username_regex.match(username):
            await interaction.response.send_message('That Reddit username appears to be invalid.', ephemeral=True)
            return

        # Does the Reddit user even exist?
        if not harmony_reddit.reddit_user_exists(username):
            await interaction.response.send_message('That Reddit user doesn\'t exist.', ephemeral=True)
            return

        reddit_user = harmony_reddit.get_redditor(username)

        verification_code = self.generate_verification_code(prefix="hwsuk_")

        # Save pending verification data to MongoDB.
        pending_verification_data = verify_models.PendingVerification(
            discord_user=verify_models.DiscordUser(
                discord_user_id=interaction.user.id,
                guild_roles=[role.id for role in interaction.user.roles]
            ),
            reddit_user=verify_models.RedditUser(
                reddit_user_id=reddit_user.id,
                reddit_username=username
            ),
            pending_verification_data=verify_models.PendingVerificationData(
                verification_code=verification_code
            )
        )

        pending_verification_data.save()

        embed = discord.Embed(
            title='Check your Reddit private messages',
            description=f'''We've sent a message containing a verification code to your Reddit account - 
            run `/verify` again and enter the code to finish verifying your account.
            
            If you don't see anything from us, please check your Reddit privacy settings.
            '''
        )

        harmony_reddit.send_verification_message(username, verification_code)

        # Send the user instructions on how to proceed.
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.send_verification_code(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_error(interaction, error)


class EnterVerificationTokenModal(discord.ui.Modal, title='Enter your verification code'):
    verification_token_field = VerificationTokenField()

    @staticmethod
    def update_db(pending_verification: verify_models.PendingVerification):
        verified_user_data = verify_models.VerifiedUser(
            discord_user=pending_verification.discord_user,
            reddit_user=pending_verification.reddit_user,
            user_verification_data=verify_models.UserVerificationData(
                requested_verification_at=pending_verification.pending_verification_data.requested_verification_at
            )
        )

        verified_user_data.save()
        pending_verification.delete()

    @staticmethod
    async def assign_role(member: discord.Member) -> None:
        """
        Assign the configured role to the specified member.
        :param member: The member to whom the role should be assigned.
        :return: Nothing.
        """
        await member.add_roles(verified_role, reason="Verified using Harmony Bot")

    async def complete_verification(self, interaction: discord.Interaction) -> None:
        entered_code = self.verification_token_field.value

        pending_verification = harmony_db.get_pending_verification(interaction.user.id)

        if pending_verification.pending_verification_data.verification_code == entered_code:
            self.update_db(pending_verification)
            await self.assign_role(interaction.user)

            await interaction.response.send_message("Done! You've successfully linked your Reddit account.",
                                                    ephemeral=True)
        else:
            await interaction.response.send_message("That code doesn't look right. Please try again.",
                                                    ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.complete_verification(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_error(interaction, error)


class UnverifyConfirmationModal(discord.ui.Modal, title="Enter your Reddit username to confirm."):
    reddit_username_field = RedditUsernameField()

    async def unverify(self, interaction: discord.Interaction):
        verification_data = harmony_db.get_verification_data(interaction.user.id)

        reddit_username = self.reddit_username_field.value

        reddit_username = reddit_username.replace('u/', '')

        if reddit_username == verification_data.reddit_user.reddit_username:
            verification_data.delete()

            await interaction.user.remove_roles(verified_role, reason="Unverified using Harmony Bot")
            await interaction.response.send_message("Unverified successfully.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "Looks like you didn't enter the correct Reddit username. Please check and try again.", ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.unverify(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_error(interaction, error)


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        whois_context_menu = app_commands.ContextMenu(
            name="Whois",
            guild_ids=[int(config["discord"]["guild_id"])],
            callback=self.whois_user
        )

        self.bot.tree.add_command(whois_context_menu)

        logger.info("Loaded verify cog.")

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
        if harmony_db.has_verification_data(interaction.user.id):
            await interaction.response.send_message(
                "Looks like you're already verified. If you can't access the server, **please raise a ticket.**",
                ephemeral=True)

            return

        if harmony_db.has_pending_verification(interaction.user.id):
            await interaction.response.send_modal(EnterVerificationTokenModal())
        else:
            await interaction.response.send_modal(EnterRedditUsernameModal())

    @app_commands.command(
        name='unverify',
        description='Unlink your Discord and Reddit accounts.'
    )
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(int(config["discord"]["guild_id"])))
    async def display_unverify_dialog(self, interaction: discord.Interaction):
        if harmony_db.has_verification_data(interaction.user.id):
            await interaction.response.send_modal(UnverifyConfirmationModal())
        elif harmony_db.has_pending_verification(interaction.user.id):
            pending_verification = harmony_db.get_pending_verification(interaction.user.id)
            pending_verification.delete()
            await interaction.response.send_message(
                "Your pending verification has been cancelled. You can `/verify` again at any time.", ephemeral=True)
        else:
            await interaction.response.send_message("Doesn't look like you're verified.", ephemeral=True)

    async def whois_user(self, interaction: discord.Interaction, member: discord.Member):
        verification_data = harmony_db.get_verification_data(member.id)

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


async def handle_error(interaction: discord.Interaction, error: Exception) -> None:
    """
    Handle an exception encountered during an interaction.
    :param interaction: The interaction in which the exception was raised.
    :param error: The raised exception.
    :return: Nothing.
    """
    error_reference = "err_".join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

    logger.warning(f"{error_reference}: An error was raised during interaction with command {interaction.command.name}")
    traceback.print_exception(type(error), error, error.__traceback__)

    embed = discord.Embed(
        title="An error occurred",
        description=f"""
        Something went wrong while processing your request.
          
        Please try again later. If the problem persists, please raise a ticket, citing the following reference:
        `{error_reference}`
        """
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verify(bot))
