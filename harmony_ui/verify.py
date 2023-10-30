import re
import typing
import random
import string
import discord
import datetime
import harmony_ui

from loguru import logger
from harmony_config import config
from harmony_services import db as harmony_db
from harmony_models import verify as verify_models
from harmony_services import reddit as harmony_reddit


configured_verify_role_data = config.get_configuration_key("roles", required=True, expected_type=list)
subreddit_name = config.get_configuration_key("reddit.subreddit_name", required=True)
verification_token_prefix = config.get_configuration_key("verify.token_prefix", required=True)
verified_role = discord.Object(config.get_configuration_key(
    "discord.verified_role_id",
    required=True,
    expected_type=int
))
user_management_role = discord.Object(config.get_configuration_key(
    "discord.harmony_management_role_id",
    required=True,
    expected_type=int
))
reddit_required_account_age = config.get_configuration_key(
    "verify.reddit_minimum_account_age_days",
    required=True,
    expected_type=int
)
discord_required_account_age = config.get_configuration_key(
    "verify.discord_minimum_account_age_days",
    required=True,
    expected_type=int
)


class UpdateRoleSelect(discord.ui.Select):
    update_role_options: typing.List[discord.components.SelectOption] = []
    for role in configured_verify_role_data:
        update_role_options.append(discord.components.SelectOption(
            label=role["role_name"],
            value=role["discord_role_id"]
        ))

    def __init__(self, target_member: discord.Member, original_interaction: discord.Interaction):
        self.target_member = target_member
        self.original_interaction = original_interaction
        super().__init__(
            options=self.update_role_options
        )

    async def callback(self, interaction: discord.Interaction) -> typing.Any:
        # Disable the dropdown box on the original interaction
        self.disabled = True
        await self.original_interaction.edit_original_response(view=self.view)

        new_discord_role_id = int(self.values[0])
        logger.info(f"Reddit role update invoked for user {self.target_member.name} ({self.target_member.id}) "
                    f"by moderator {interaction.user.name}, new Discord role ID: {new_discord_role_id}")

        new_response = "The following operations were completed successfully:\n\n"

        # Cleanup any existing roles
        configured_member_role_ids = [role.id for role in self.target_member.roles]
        for role in configured_verify_role_data:
            if role["discord_role_id"] in configured_member_role_ids:
                await self.target_member.remove_roles(
                    discord.Object(role["discord_role_id"]),
                    reason="Removed by Harmony bot during Reddit flair update"
                )

        verify_role = [role for role in configured_verify_role_data if role["discord_role_id"] == new_discord_role_id][
            0]

        # Give the user their new trade role.
        new_role = discord.Object(new_discord_role_id)
        await self.target_member.add_roles(
            new_role,
            reason="Added by Harmony bot during Reddit flair update"
        )

        new_response += f"- Granted the **{verify_role['role_name']}** Discord role to **{self.target_member.name}**."
        await interaction.response.send_message(new_response, ephemeral=True)

        verification_data = harmony_db.get_verification_data(discord_user_id=self.target_member.id)

        # Give the user their new Reddit flair.
        harmony_reddit.update_user_flair(
            verification_data.reddit_user.reddit_username,
            verify_role["reddit_flair_text"],
            verify_role["reddit_flair_css_class"]
        )

        new_response += f"\n- Updated subreddit flair for u/**{verification_data.reddit_user.reddit_username}**."
        await interaction.edit_original_response(content=new_response)

        # Update our role ID bookkeeping.
        verification_data.discord_user.guild_roles = [role.id for role in self.target_member.roles]
        verification_data.save()

        new_response += f"\n- Updated verification data for u/**{verification_data.reddit_user.reddit_username}**."
        new_response += ("\n\n**All done!** Please check the subreddit if you want to verify the new flair "
                         "has been applied correctly.")
        await interaction.edit_original_response(content=new_response)


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
            placeholder=verification_token_prefix,
            required=True
        )


class EnterRedditUsernameModal(discord.ui.Modal, title='Verify your Reddit account'):
    reddit_username_field = RedditUsernameField()

    @staticmethod
    def generate_verification_code(prefix: str = "") -> str:
        chars = string.digits + string.ascii_letters
        code = ''.join(random.choice(chars) for _ in range(12))

        return f"{prefix}{code}"

    async def send_account_age_not_met_modal(
            self,
            interaction: discord.Interaction,
            account_type: typing.Literal["Discord", "Reddit"],
            required_age_days: int
    ) -> typing.NoReturn:
        await interaction.response.send_message(
            embed=harmony_ui.verify.create_account_age_requirement_not_met_embed(
                account_type=account_type,
                required_age_days=required_age_days
            ),
            ephemeral=True
        )

    async def send_verification_code(self, interaction: discord.Interaction) -> typing.NoReturn:
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

        verification_code = self.generate_verification_code(prefix=verification_token_prefix)

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

        harmony_reddit.send_verification_message(
            username,
            verification_code,
            subreddit_name,
            interaction.guild.name
        )

        # Send the user instructions on how to proceed.
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction) -> typing.NoReturn:
        username = self.reddit_username_field.value.replace('u/', '')
        discord_account_age_days = (datetime.datetime.now(tz=datetime.timezone.utc) - interaction.user.created_at).days

        if harmony_reddit.get_account_age_days(username) < reddit_required_account_age:
            await self.send_account_age_not_met_modal(
                interaction, "Reddit", reddit_required_account_age
            )
        elif discord_account_age_days < discord_required_account_age:
            await self.send_account_age_not_met_modal(
                interaction, "Discord", discord_required_account_age
            )
        else:
            await self.send_verification_code(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> typing.NoReturn:
        await harmony_ui.handle_error(interaction, error)


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
    async def assign_role(member: discord.Member) -> typing.NoReturn:
        """
        Assign the configured role to the specified member.
        :param member: The member to whom the role should be assigned.
        :return: Nothing.
        """
        await member.add_roles(verified_role, reason="Verified using Harmony Bot")

    async def complete_verification(self, interaction: discord.Interaction) -> typing.NoReturn:
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

    async def on_submit(self, interaction: discord.Interaction) -> typing.NoReturn:
        await self.complete_verification(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> typing.NoReturn:
        await harmony_ui.handle_error(interaction, error)


class UnverifyConfirmationModal(discord.ui.Modal, title="Enter your Reddit username to confirm."):
    reddit_username_field = RedditUsernameField()

    async def unverify(self, interaction: discord.Interaction):
        verification_data = harmony_db.get_verification_data(discord_user_id=interaction.user.id)

        reddit_username = self.reddit_username_field.value

        reddit_username = reddit_username.replace('u/', '')

        if reddit_username == verification_data.reddit_user.reddit_username:
            verification_data.delete()

            await interaction.user.remove_roles(verified_role, reason="Unverified using Harmony Bot")
            await interaction.response.send_message("Unverified successfully.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "Looks like you didn't enter the correct Reddit username. Please check and try again.", ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction) -> typing.NoReturn:
        await self.unverify(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> typing.NoReturn:
        await harmony_ui.handle_error(interaction, error)


class UpdateRoleView(discord.ui.View):
    def __init__(self, target_member: discord.Member, original_interaction: discord.Interaction):
        super().__init__()
        self.add_item(UpdateRoleSelect(target_member, original_interaction))

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) \
            -> typing.NoReturn:
        await harmony_ui.handle_error(interaction, error)


def create_nonexistent_reddit_account_embed(username: str, guild_name: str) -> discord.Embed:
    return discord.Embed(
        title="Your Reddit account doesn't exist",
        description=f"""
        It looks like your Reddit account, **u/{username}**, doesn't exist anymore.
        
        Access to privileged channels in {guild_name} requires a verified Reddit account, so your access has been removed. Please use `/verify` again with a valid Reddit account to regain access.
        
        If you think this is in error, please contact the moderation team.
        """
    )


def create_suspended_reddit_account_embed(username: str, guild_name: str) -> discord.Embed:
    return discord.Embed(
        title="Your Reddit account has been suspended",
        description=f"""
        It looks like your Reddit account, **u/{username}**, has been suspended.

        Access to privileged channels in {guild_name} requires a verified Reddit account, so your access has been removed. Please use `/verify` again with a valid Reddit account to regain access.

        If you think this is in error, please contact the moderation team.
        """
    )


def create_banned_reddit_account_embed(username: str, guild_name: str, subreddit_name: str) -> discord.Embed:
    return discord.Embed(
        title=f"Your Reddit account is banned from r/{subreddit_name}",
        description=f"""
        It looks like your Reddit account, **u/{username}**, has been banned from participating in r/{subreddit_name}.

        Access to the {guild_name} Discord server requires that your subreddit account is in good standing. As a result, you have been banned from the server.

        If you think this is in error, please contact the moderation team.
        """
    )


def create_no_verification_data_embed(guild_name: str, subreddit_name: str) -> discord.Embed:
    return discord.Embed(
        title=f"You don't seem to have a verified Reddit account",
        description=f"""
        It looks like you don't have a verified Reddit account.

        Access to certain parts of the {guild_name} Discord server requires that you link a Reddit account that isn't banned from r/{subreddit_name}. As a result, your access has been removed.
        
        Not to worry! You can fix this by typing `/verify` in any of the channels you still have access to, and following the steps to link your Reddit account.

        If you think this is in error, please contact the moderation team.
        """
    )


def create_account_age_requirement_not_met_embed(
        account_type: typing.Literal["Discord", "Reddit"],
        required_age_days: int
):
    return discord.Embed(
        title=f"Your {account_type} account is too new",
        description=f"""
        To link your Reddit and Discord accounts, your {account_type} account needs to be at least {required_age_days} days old.
        
        Please try again when your {account_type} account is old enough to meet these requirements. 
        """
    )