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


# Load cogs

# Run bot
bot.run(config.token)
