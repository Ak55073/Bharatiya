import discord


class ConfirmationView(discord.ui.View):
    def __init__(self, confirm='Confirming', cancel='Cancelling'):
        super().__init__()
        self.value = None
        self.confirm = confirm
        self.cancel = cancel

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.confirm is None:
            await interaction.response.defer()
        else:
            await interaction.response.send_message(self.confirm, ephemeral=True)
        self.value = True
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cancel is None:
            await interaction.response.defer()
        else:
            await interaction.response.send_message(self.cancel, ephemeral=True)
        self.value = False
        self.stop()
