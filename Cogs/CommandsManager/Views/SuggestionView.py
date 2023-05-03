import discord


class Suggestion(discord.ui.Modal, title='Suggestion'):
    name = discord.ui.TextInput(
        label='Name',
        placeholder='OPTIONAL',
        required=False,
    )

    server = discord.ui.TextInput(
        label='Server',
        placeholder='OPTIONAL',
        required=False,
    )

    feedback = discord.ui.TextInput(
        label='What do you think of this new feature?',
        style=discord.TextStyle.long,
        placeholder='Type your feedback here...',
        required=True
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        message = f"By {self.name.value} of {self.server.value} \n{self.feedback.value}"
        owner = await self.bot.fetch_user(str(self.bot.owner_id))
        await owner.send(message)

        await interaction.response.send_message(f'Thanks for your feedback {self.name.value}!', ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong. Try again!', ephemeral=True)
