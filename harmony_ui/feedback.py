import typing
import discord
import harmony_ui
import mongoengine
import harmony_services.db
import harmony_models.feedback


class FeedbackTitleField(discord.ui.TextInput):
    def __init__(self):
        super().__init__(
            label='Feedback title',
            required=True,
            max_length=200
        )


class FeedbackDescriptionField(discord.ui.TextInput):
    def __init__(self):
        super().__init__(
            label='Feedback description',
            required=True,
            max_length=1500,
            style=discord.TextStyle.long
        )


class FeedbackItemView(discord.ui.View):
    upvote_weight = 1
    downvote_weight = -1

    def __init__(self):
        """
        Create the FeedbackItemView which allows users to vote on feedback items.
        """
        super().__init__(timeout=None)

    @discord.ui.button(label="Upvote", style=discord.ButtonStyle.green, row=1, custom_id="feedback_upvote_button")
    async def upvote(self, interaction: discord.Interaction, _: discord.ui.Button) -> typing.NoReturn:
        await self.process_vote(interaction, self.upvote_weight)

    @discord.ui.button(label="Downvote", style=discord.ButtonStyle.red, row=1, custom_id="feedback_downvote_button")
    async def downvote(self, interaction: discord.Interaction, _: discord.ui.Button) -> typing.NoReturn:
        await self.process_vote(interaction, self.downvote_weight)

    async def process_vote(
            self,
            interaction: discord.Interaction,
            new_vote_weight: int
    ) -> typing.NoReturn:
        """
        Process a user vote.
        :param interaction: The interaction that triggered the vote.
        :param new_vote_weight: The new vote weight.
        :return: Nothing.
        """
        feedback_item = harmony_services.db.get_feedback_data(interaction.message.id)

        # Is the user trying to vote on their own feedback?
        if feedback_item.author_username == interaction.user.name:
            await interaction.response.send_message(
                ":no_entry_sign: You can't vote on your own feedback.",
                ephemeral=True
            )

            return

        # Has the user already voted?
        vote = self.get_vote(interaction.user.name, feedback_item)

        if vote:
            # If they're trying to vote in the same direction as before, then don't let them.
            if vote.vote_weight == new_vote_weight:
                await interaction.response.send_message(
                    ":no_entry_sign: Looks like you've already voted on this feedback - you can only vote once.",
                    ephemeral=True
                )

                return
            # Otherwise, update their existing vote to point the other way.
            else:
                vote.vote_weight = new_vote_weight
                feedback_item.save()

                await interaction.response.send_message(
                    ":inbox_tray: Your vote has been updated.",
                    ephemeral=True
                )

                await self.update_view(interaction, feedback_item)

                return

        feedback_item.votes.create(
            discord_username=interaction.user.name,
            vote_weight=new_vote_weight
        )

        feedback_item.save()

        await interaction.response.send_message(
            ":inbox_tray: Your vote has been cast.",
            ephemeral=True
        )

        await self.update_view(interaction, feedback_item)

    async def update_view(self, interaction: discord.Interaction, feedback_item: harmony_models.feedback.FeedbackItem):
        upvote_count = (
            sum([vote.vote_weight
                 for vote in feedback_item.votes
                 if vote.vote_weight == self.upvote_weight]))

        downvote_count = (
            abs(sum([vote.vote_weight
                     for vote in feedback_item.votes
                     if vote.vote_weight == self.downvote_weight])))

        await interaction.message.edit(
            embed=create_feedback_embed(
                feedback_item.feedback_title,
                feedback_item.feedback_description,
                feedback_item.author_username,
                upvote_count,
                downvote_count
            ),
            view=self
        )

    @staticmethod
    def get_vote(username: str, feedback_item: harmony_models.feedback.FeedbackItem) \
            -> typing.Optional[harmony_models.feedback.FeedbackVote]:
        """
        Get a user's vote on an item.
        :param username: The Discord username of the user to get the vote for.
        :param feedback_item: The item to query for votes.
        :return: The vote if a user has already voted, otherwise None.
        """
        try:
            return feedback_item.votes.get(discord_username=username)
        except mongoengine.DoesNotExist:
            return None


class CreateFeedbackItemModal(discord.ui.Modal):
    feedback_title_field = FeedbackTitleField()
    feedback_description_field = FeedbackDescriptionField()

    def __init__(self, feedback_channel: discord.TextChannel):
        super().__init__(title='Create a feedback item')

        self.feedback_channel = feedback_channel

    async def on_submit(self, interaction: discord.Interaction) -> typing.NoReturn:
        await interaction.response.defer(ephemeral=True, thinking=True)

        message = await self.feedback_channel.send(":crystal_ball: I predict a new feedback item...")

        # Save the feedback item to the database
        feedback_item = harmony_models.feedback.FeedbackItem(
            author_username=interaction.user.name,
            feedback_title=self.feedback_title_field.value,
            feedback_description=self.feedback_description_field.value,
            discord_message_id=message.id
        )

        feedback_item.save()

        await message.edit(
            content=None,
            embed=create_feedback_embed(
                feedback_title=feedback_item.feedback_title,
                feedback_description=feedback_item.feedback_description,
                feedback_author=interaction.user.name,
                feedback_upvotes=0,
                feedback_downvotes=0
            ),
            view=FeedbackItemView()
        )

        await interaction.followup.send(":inbox_tray: Thanks! Your feedback has been created.")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> typing.NoReturn:
        await harmony_ui.handle_error(interaction, error)


def create_feedback_embed(
        feedback_title: str,
        feedback_description: str,
        feedback_author: str,
        feedback_upvotes: int,
        feedback_downvotes: int
) -> discord.Embed:
    vote_score: str = format_vote_score(feedback_upvotes, feedback_downvotes)
    embed_color: int = get_embed_color(feedback_upvotes, feedback_downvotes)

    return discord.Embed(
        title=f"Feedback from {feedback_author}: {feedback_title}",
        description=feedback_description,
        color=embed_color
    ).set_footer(text=f"This feedback has a score of {vote_score} "
                      f"({feedback_upvotes} upvotes, {feedback_downvotes} downvotes)")


def format_vote_score(feedback_upvotes: int, feedback_downvotes: int) -> str:
    """
    Calculate and format the total vote score, adding a leading sign no matter the value.
    :param feedback_upvotes: The number of upvotes.
    :param feedback_downvotes: The number of downvotes.
    :return: The formatted total score, with a leading sign.
    """
    total_score = feedback_upvotes - feedback_downvotes
    sign = "+" if total_score > 0 else "±" if total_score == 0 else ""

    return f"{sign}{total_score}"


def get_embed_color(feedback_upvotes: int, feedback_downvotes: int) -> int:
    """
    Get the embed color based on the current vote score.
    :param feedback_upvotes: The number of upvotes.
    :param feedback_downvotes: The number of downvotes.
    :return: The color, as a 24-bit hex value.
    """
    total_score = feedback_upvotes - feedback_downvotes

    if total_score > 0:
        return 0x40BD63
    elif total_score < 0:
        return 0xBD404D
    else:
        return 0x40AABD