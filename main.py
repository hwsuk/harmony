import json
import discord

from loguru import logger
from discord import app_commands

with open('config.json', 'r') as f:
    config = json.load(f)

TEST_GUILD = discord.Object(config["discord"]["guild_id"])


class MyClient(discord.Client):
    def __init__(self) -> None:
        # Just default intents and a `discord.Client` instance
        # We don't need a `commands.Bot` instance because we are not
        # creating text-based commands.
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        # We need an `discord.app_commands.CommandTree` instance
        # to register application commands (slash commands in this case)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    async def setup_hook(self) -> None:
        # Sync the application command with Discord.
        await self.tree.sync(guild=TEST_GUILD)


class RedditUsernameField(discord.ui.TextInput):
    def __init__(self):
        super().__init__(label="Please enter your Reddit username.", placeholder="u/cool_dude", required=True)


class VerifyRedditModal(discord.ui.Modal, title='Verify your Reddit account'):
    reddit_username = RedditUsernameField()

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Verify command invoked with username value {self.reddit_username.value}')


client = MyClient()


@client.tree.command(
    guild=config["discord"]["guild_id"],
    description="Submit feedback"
)
async def verify(interaction: discord.Interaction):
    # Send the modal with an instance of our `Feedback` class
    # Since modals require an interaction, they cannot be done as a response to a text command.
    # They can only be done as a response to either an application command or a button press.
    await interaction.response.send_modal(VerifyRedditModal())


client.run(config["discord"]["bot_token"])
