import disnake
from disnake.ext import commands
import config

test_guilds = [1097277537404583956]

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.InteractionBot(intents=intents, test_guilds=test_guilds)


# Setup presence and print some info
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('-------------------')
    await bot.change_presence(activity=disnake.Game(name="Version " + config.version))
    print('status set.')
    print('-------------------')

    # channel = bot.get_channel(1136446702925135872)
    # msg = channel.get_partial_message(1193741565399666749)
    # await msg.edit(embed=disnake.Embed(
    #     title="Roles",
    #     description="Click the reactions below to select the corresponding roles.\n\n:tickets: - Notifications for Movie Night\n:video_game: - Notifications for Game Night\n<:paytsyipsmol:1127046949871292608> - Notifications for Every Paytsyìp Post\n:tv: - Notifications for Spontaneous TV Shows in VC\n:wrench: - Notifications for Na'vi Resource Developers",
    #     colour=0x4ab5b5
    # ))


# Load cogs

# Run bot
bot.run(config.token)
