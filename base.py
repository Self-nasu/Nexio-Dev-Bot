import discord
from discord.ext import commands

class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash command: Ping
    @discord.app_commands.command(name="ping", description="Responds with Pong!")
    async def ping(self, interaction: discord.Interaction):
        """Responds with Pong!"""
        await interaction.response.send_message("Pong! 🏓 by Nasu")

# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(ExampleCog(bot))
