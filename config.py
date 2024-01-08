# ------------------------------------------------- #
#              Bot Configuration File               #
# ------------------------------------------------- #

# Open token file (so the repository doesn't receive the token and the config can still be pushed)
with open('token.txt', 'r') as file:
    token = file.read()

# System Basics
token = token.strip()
description = "I think I'm a useful bot."
version = "1.0.0"
repository = "https://github.com/Kelutral-org/ewo-bot"
test_server_link = "https://discord.gg/B9rT2mHJTW"
discord_library = "Disnake"
operators = [423581502970789889, 189504650645471232, 205370567614922753, 429361033446948864, 81105065955303424]
