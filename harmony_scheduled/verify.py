import json
import discord
import prawcore.exceptions
import harmony_ui
import harmony_ui.verify

from loguru import logger
from discord.ext import tasks, commands
from harmony_services import db as harmony_db
from harmony_services import reddit as harmony_reddit


with open("config.json", "r") as f:
    config = json.load(f)

subreddit_name = config["reddit"]["subreddit_name"]
verified_role_id = config["discord"]["verified_role_id"]
verified_role = discord.Object(verified_role_id)


@tasks.loop(seconds=config["schedule"]["reddit_account_check_interval_seconds"])
async def check_reddit_accounts_task(bot: commands.Bot):
    """
    Check Reddit accounts to make sure they haven't been banned from the subreddit, or deleted their account.
    :param bot: A reference to the bot instance used for Discord operations.
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
        guild = await bot.fetch_guild(int(config["discord"]["guild_id"]))

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
        subreddit_bans = [redditor.name for redditor in
                          harmony_reddit.subreddit_bans(subreddit_name, limit=bans_fetch_limit)]

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

            removal_data = {
                "reddit_username": reddit_username,
                "discord_member_name": member.name,
                "removal_reason": None,
                "user_notified": True
            }

            try:
                reddit_user_exists = harmony_reddit.reddit_user_exists(reddit_username)
                reddit_account_suspended = harmony_reddit.redditor_suspended(reddit_username)
                reddit_account_sub_banned = reddit_username in subreddit_bans
            except prawcore.exceptions.TooManyRequests:
                logger.warning(f"Hit Reddit rate limit while processing member {member.name}, ignoring for now.")
                continue

            if not reddit_user_exists:
                logger.info(f"Member {member.name}'s Reddit account no longer exists: u/{reddit_username}")
                removal_data["removal_reason"] = "Reddit account no longer exists"

                if not dry_run:
                    await member.remove_roles(
                        verified_role,
                        reason="User's Reddit account no longer exists."
                    )

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
                        removal_data["user_notified"] = False

                    user.delete()

                removed_users.append(removal_data)
                continue

            if reddit_account_suspended:
                logger.info(f"Member {member.name}'s Reddit account is suspended: u/{reddit_username}")
                removal_data["removal_reason"] = "Reddit account is suspended"

                if not dry_run:
                    await member.remove_roles(
                        verified_role,
                        reason=f"User's Reddit account (u/{reddit_username}) is suspended."
                    )

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
                        removal_data["user_notified"] = False

                    user.delete()

                removed_users.append(removal_data)
                continue

            if reddit_account_sub_banned:
                logger.info(f"Member {member.name}'s Reddit account (u/{reddit_username}) "
                            f"is banned from r/{subreddit_name}")
                removal_data["removal_reason"] = f"Reddit account is banned from r/{subreddit_name}"

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
                        removal_data["user_notified"] = False

                    await member.ban(
                        reason=f"Linked reddit account u/{reddit_username} is banned from r/{subreddit_name}"
                    )

                    user.delete()
                continue

        report_message = f"All verified Reddit users checked. "

        if removed_users:
            report_message += f"{len(removed_users)} users were processed:\n\n"

            for removed_user in removed_users:
                report_message += (f"- **u/{removed_user['reddit_username']}** / "
                                   f"{removed_user['discord_member_name']}: {removed_user['removal_reason']}\n")
        else:
            report_message += "No users were processed."

        failed_notifications = [removed_user for removed_user in removed_users if not removed_user["user_notified"]]
        if failed_notifications:
            report_message += "\nThe following users could not be notified due to an error:\n\n"
            for failed_notification in failed_notifications:
                report_message += f"- **u/{failed_notification['reddit_username']}\n"

        if dry_run:
            report_message += "\n:information_source: No action has been taken - this is a dry run."

        await reporting_channel.send(content=report_message)

    except Exception as e:
        logger.error(f"Something went wrong while running the Reddit accounts ban check job.")

        if reporting_channel and isinstance(reporting_channel, discord.TextChannel):
            await reporting_channel.send(content="## Something went wrong when checking Reddit users!\n\n"
                                                 "Please check the bot logs for more details.")

        raise e


@tasks.loop(seconds=config["schedule"]["discord_role_check_interval_seconds"])
async def check_discord_roles_task(bot: commands.Bot):
    """
    Check all users of the configured verified role ID to see if they have data in the DB.
    If not, then remove them, and let them know.
    :param bot: A reference to the bot instance used for Discord operations.
    :return: Nothing.
    """
    job_enabled: bool = config["schedule"]["discord_role_check_enabled"]

    if not job_enabled:
        logger.info("Scheduled Discord verified role check is disabled.")
        return

    reporting_channel = None
    removed_users = []
    dry_run = config["schedule"]["discord_role_check_dry_run"]
    report_message = ""

    try:
        guild = bot.get_guild(int(config["discord"]["guild_id"]))

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

        logger.info("Running scheduled job to cleanup Discord users without verification data.")

        verified_guild_role = guild.get_role(verified_role_id)

        if not verified_guild_role:
            raise Exception(f"Configured verified role with ID {verified_role_id} could not be found.")

        for member in verified_guild_role.members:
            if not harmony_db.has_verification_data(member.id):
                removal_data = {
                    "discord_member_name": member.name,
                    "removal_reason": "No linked Reddit account found.",
                    "user_notified": True
                }

                logger.info(f"Member {member.name} has the {verified_guild_role.name} role "
                            f"without a linked Reddit account, removing.")

                if not dry_run:
                    await member.remove_roles(
                        verified_role,
                        reason="User does not have a linked Reddit account."
                    )

                    try:
                        await member.send(
                            embed=harmony_ui.verify.create_no_verification_data_embed(
                                guild_name=guild.name,
                                subreddit_name=subreddit_name
                            )
                        )
                    except Exception:
                        logger.warning(f"Failed to notify {member.name} that their verified role has been revoked.")
                        removal_data["user_notified"] = False

                removed_users.append(removal_data)

        report_message = f"All members of the {verified_guild_role.name} role have been checked. "

        if removed_users:
            report_message += (f"{len(removed_users)} users were removed due to missing verification data.\n\n"
                               f"Please see the bot logs for more details.")
        else:
            report_message += f"No users were missing verification data."

        if dry_run:
            report_message += "\n\n:information_source: No action was taken - this is a dry run."

        await reporting_channel.send(content=report_message)

    except Exception as e:
        logger.error(f"Something went wrong while running the Discord verified role check job.")

        if reporting_channel and isinstance(reporting_channel, discord.TextChannel):
            await reporting_channel.send(content="## Something went wrong when checking Discord roles!\n\n"
                                                 "Please check the bot logs for more details.")

        raise e