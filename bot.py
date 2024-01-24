import logging
import os
import config
import cogs.wordgame.wordgame
import disnake
from disnake.ext import commands

if not os.path.exists("logs"):
    os.mkdir("logs")
logger = logging.getLogger('paytsyìp')
logger.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('[%(asctime)s]  [%(levelname)s]  [%(name)s]    %(message)s', "%Y-%m-%d %H:%M:%S")
log_file = logging.FileHandler("logs/latest.log", "w", "utf-8")
log_file.setFormatter(file_formatter)
logger.addHandler(log_file)
console = logging.StreamHandler()
console_formatter = logging.Formatter('\033[33m[%(asctime)s]  [%(levelname)s]  [%(name)s]    %(message)s\033[0m', "%Y-%m-%d %H:%M:%S")
console.setFormatter(console_formatter)
logger.addHandler(console)

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.InteractionBot(intents=intents, test_guilds=config.test_guilds)


# Setup presence and print some info
@bot.event
async def on_ready():
    await bot.change_presence(activity=disnake.Game(name="Version " + config.version))
    logger.info('--------------------- ONLINE ---------------------')
    logger.info('Name: ' + bot.user.name)
    logger.info('ID: ' + str(bot.user.id))
    logger.info('Status: ' + bot.status.value)
    logger.info('--------------------------------------------------')

# Add cogs
bot.add_cog(cogs.wordgame.wordgame.WordgameCog(bot))

# Run bot
bot.run(config.token)
