import json
import typing
import mongoengine

import harmony_models.verify as verify_models

with open("config.json", "r") as f:
    config = json.load(f)

db_name = config["db"]["db_name"]
db_host = config["db"]["hostname"]
db_port = config["db"]["port"]
db_username = config["db"]["username"]
db_password = config["db"]["password"]
db_replica_set = config["db"]["replica_set_name"]

connection = mongoengine.connect(
    host=f"mongodb://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}?replicaSet={db_replica_set}"
)


def get_pending_verification(discord_user_id: int) -> typing.Optional[verify_models.PendingVerification]:
    """
    Fetch a pending verification from the database.
    :param discord_user_id: The Discord user to fetch the pending verification for.
    :return: The pending verification, if found, otherwise None.
    """
    return verify_models.PendingVerification.objects(discord_user__discord_user_id=discord_user_id).first()


def has_pending_verification(discord_user_id: int) -> bool:
    """
    Check if a Discord user has a pending verification.
    :param discord_user_id: The user ID to check.
    :return: True if the user has a pending verification, otherwise False.
    """
    return get_pending_verification(discord_user_id) is not None


def get_verification_data(discord_user_id: int = None,
                          reddit_username: str = None) -> typing.Optional[verify_models.VerifiedUser]:
    """
    Fetch a Discord user's verification data from the database.
    :param discord_user_id: The Discord user ID to fetch the verification for.
    :param reddit_username: The Reddit username to fetch the verification for.
    :return: The verification data, if found, otherwise None.
    """
    if discord_user_id:
        return verify_models.VerifiedUser.objects(discord_user__discord_user_id=discord_user_id).first()
    if reddit_username:
        return verify_models.VerifiedUser.objects(reddit_user__reddit_username=reddit_username).first()

    return None


def has_verification_data(discord_user_id: int) -> bool:
    """
    Check if a Discord user has verification data.
    :param discord_user_id: The user ID to check.
    :return: True if the user has verification data, otherwise False.
    """
    return get_verification_data(discord_user_id=discord_user_id) is not None
