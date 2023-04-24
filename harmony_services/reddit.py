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
    :param username: The username, beginning with u/, of the Reddit user to check.
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
    :param username: The Redditor's u/username.
    :return: The Redditor, if it exists, otherwise None.
    """
    try:
        return reddit.redditor(username)
    except prawcore.exceptions.NotFound:
        return None
