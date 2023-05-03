import discord

# TODO: Optimised
class RoleViewAssign(discord.ui.View):
    def __init__(self, parent, db_driver):
        super().__init__(timeout=None)
        self.parent = parent
        self.db_driver = db_driver

    async def interaction_check(self, interaction, /) -> bool:
        data = self.db_driver.fetch_rm_server(server_id=interaction.guild.id)
        if not data.enabled:
            await interaction.response.send_message(
                f"Self assign is not activated in this server. use '/role-manager enable'"
            )
            await interaction.channel.purge()
            return False
        return True

    @discord.ui.button(label='Add', style=discord.ButtonStyle.green, custom_id='auto_assign:add')
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = self.db_driver.fetch_rm_server(server_id=interaction.guild.id)
        if not data.enabled:
            await interaction.response.send_message("Command unavailable. "
                                                    "Role Manager is not activated in this server.",
                                                    ephemeral=True)
            return
        role = interaction.guild.get_role(int(interaction.message.embeds[0].description))
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"<@&{role.id}> added successfully.", delete_after=5, ephemeral=True)

    @discord.ui.button(label='Remove', style=discord.ButtonStyle.red, custom_id='auto_assign:remove')
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = self.db_driver.fetch_rm_server(server_id=interaction.guild.id)
        if not data.enabled:
            await interaction.response.send_message("Command unavailable. "
                                                    "Role Manager is not activated in this server.",
                                                    ephemeral=True)
            return
        role = interaction.guild.get_role(int(interaction.message.embeds[0].description))
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"<@&{role.id}> removed successfully.", delete_after=5, ephemeral=True)

    @discord.ui.button(label='View', style=discord.ButtonStyle.blurple, custom_id='auto_assign:view')
    async def view(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = interaction.guild.get_role(int(interaction.message.embeds[0].description))

        embed = discord.Embed(title=role.name, description="", color=role.color)
        embed.set_author(name='Bhartiya',
                         icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                                  "/1610303189d607b5665cba3d037226b7.webp?size=128")

        embed.add_field(name='Mentionable',
                        value=role.mentionable,
                        inline=True)
        embed.add_field(name='Created',
                        value=str(role.created_at)[:19],
                        inline=True)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='Member Count',
                        value=len(role.members),
                        inline=True)
        embed.add_field(name='Guild',
                        value=role.guild.name,
                        inline=True)

        embed.add_field(name='', value="Role ID:", inline=False)
        embed.set_footer(text=role.id)

        await interaction.response.send_message(embed=embed, delete_after=30, ephemeral=True)

    async def on_error(self, interaction, error: Exception, item, /) -> None:
        if isinstance(error, AttributeError):
            await self.parent.refresh_server_manual(interaction.guild.id)
        else:
            print("Failed to self assign role", error)
