import json
import typing

import praw.models
import prawcore.exceptions

with open('./config.json', 'r') as config_file:
    config = json.load(config_file)

reddit = praw.Reddit(
    client_id=config['reddit']['client_id'],
    client_secret=config['reddit']['client_secret'],
    username=config['reddit']['username'],
    password=config['reddit']['password'],
    user_agent=config['reddit']['user_agent'],
    check_for_async=False
)


def reddit_user_exists(username: str) -> bool:
    """
    Check if a Reddit user exists.
    :param username: The username, not beginning with u/, of the Reddit user to check.
    :return: True if the Redditor exists, False otherwise.
    """
    try:
        reddit.redditor(username).id
    except prawcore.exceptions.NotFound:
        return False

    return True


def get_redditor(username: str) -> typing.Optional[praw.models.Redditor]:
    """
    Get a specified Redditor.
    :param username: The Redditor's username, not beginning with u/.
    :return: The Redditor, if it exists, otherwise None.
    """
    try:
        return reddit.redditor(username)
    except prawcore.exceptions.NotFound:
        return None


def send_verification_message(username: str, verification_code: str) -> None:
    """
    Send a message to the user with their verification code in it.
    :param username: The user to send the message to.
    :param verification_code: The verification code to include in the message.
    :return: Nothing.
    """

    if not reddit_user_exists(username):
        raise RuntimeError("The specified Reddit user doesn't exist.")

    redditor = get_redditor(username)

    message_contents = f"""Hey u/{username},

You recently requested to verify your account on the HardwareSwapUK Discord server.

To complete verification, run the `/verify` command again, and enter the following verification code:

`{verification_code}`

If this wasn't you, please send a modmail to /r/HardwareSwapUK.

Thanks,

The /r/HardwareSwapUK mod team

---

This message was sent by the Harmony Discord bot, created by the team at /r/HardwareSwapUK. To learn more about what data this bot collects about you, please [click here](https://privacy.hardwareswap.uk).
"""

    redditor.message(subject="Your /r/HardwareSwapUK Discord verification code", message=message_contents)
