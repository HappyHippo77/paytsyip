import disnake
from disnake.ext import commands
import util

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.purge_user = None

    def is_user(self, message):
        return message.author == self.purge_user

    @commands.slash_command(name="purge", description="Delete all messages in the current channel from a user.",
                            default_member_permissions=disnake.Permissions(manage_messages=True))
    async def purge(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User, amount: int = None):
        self.purge_user = user
        await inter.channel.purge(limit=amount, check=self.is_user)
        await inter.response.send_message(embed=util.successEmbed(util.i18n('admin.purge') % ('all' if amount is None else amount, user.display_name, '#' + inter.channel.name)), ephemeral=True)
        self.purge_user = None
