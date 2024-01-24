import disnake
import config
import json


with open("lang/en.json", "r", encoding="utf-8") as f:
    lang = json.load(f)


def i18n(key: str) -> str:
    return lang.get(key)


def successEmbed(description: str):
    return disnake.Embed(color=config.success_color,
                         title=i18n("title.success"),
                         description=description)


def errorEmbed(description: str):
    return disnake.Embed(color=config.error_color,
                         title=i18n("title.error"),
                         description=description)
