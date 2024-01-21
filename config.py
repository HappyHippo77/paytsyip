import json

# Open token file (so the repository doesn't receive the token and the config can still be pushed)
with open('token.txt', 'r') as file:
    token = file.read()

# System Basics
token = token.strip()
description = "I think I'm a useful bot."
version = "1.0.1"
repository = "https://github.com/HappyHippo77/paytsyip"
discord_library = "Disnake"

neutral_color = 0x4ab5b5
error_color = 0xf54a45
success_color = 0x34c724
