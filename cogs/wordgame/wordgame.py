import pprint
import random
from enum import Enum
import disnake
from disnake.ext import commands
import sqlite3
import config
import util
from reykunyu_py import reykunyu
from reykunyu_py.errors import NoPronunciationError


def create_connection(path):
    connection = None
    try:
        connection = sqlite3.connect(path)
        print("Connection to SQLite DB successful")
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")
    return connection


database = create_connection('cogs/wordgame/wordgame.db')


def write_to_db(query):
    cursor = database.cursor()
    try:
        cursor.execute(query)
        database.commit()
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")


def read_from_db(query):
    cursor = database.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")


def enable_channel(channel_id: int, guild_id: int) -> disnake.Embed:
    if not read_from_db("SELECT * FROM channels WHERE channel_id = %s AND guild_id = %s" % (channel_id, guild_id)):
        write_to_db("INSERT INTO channels (channel_id, guild_id) VALUES (%s, %s)" % (channel_id, guild_id))
        return util.successEmbed(util.i18n("wordgame.enabled_channel") % channel_id)
    else:
        return util.errorEmbed(util.i18n("wordgame.channel_already_enabled") % channel_id)


def disable_channel(channel_id: int, guild_id: int) -> disnake.Embed:
    if read_from_db("SELECT * FROM channels WHERE channel_id = %s AND guild_id = %s" % (channel_id, guild_id)):
        write_to_db("DELETE FROM channels WHERE channel_id = %s AND guild_id = %s" % (channel_id, guild_id))
        return util.successEmbed(util.i18n("wordgame.disabled_channel") % channel_id)
    else:
        return util.errorEmbed(util.i18n("wordgame.channel_already_disabled") % channel_id)


dictionary = reykunyu.dictionary

pprint.pprint(dictionary)


# Returns None if the input is not a Na'vi word.
def to_monographic(navi: str) -> str | None:
    syllables = []
    try:
        syllables = dictionary.get(navi).best_pronunciation.raw[0]
    except NoPronunciationError:
        syllables.append(navi)
    except AttributeError:
        return None

    string = ""

    for syllable in syllables:
        string += (syllable.replace('ng', 'ŋ').replace('ay', 'à').replace('ey', 'è')
                   .replace('aw', 'á').replace('ew', 'é').replace('ll', 'ʟ')
                   .replace('rr', 'ʀ').replace('ts', 'c').replace('px', 'b')
                   .replace('tx', 'd').replace('kx', 'g')).replace('ù', 'u').lower()

    return string


def from_monographic(monographic: str) -> str:
    return (monographic.replace('b', 'px').replace('d', 'tx').replace('g', 'kx')
            .replace('ŋ', 'ng').replace('à', 'ay').replace('è', 'ey')
            .replace('á', 'aw').replace('é', 'ew').replace('ʟ', 'll')
            .replace('ʀ', 'rr').replace('c', 'ts'))


class InvalidReason(Enum):
    diphthong = 1
    diacritic = 2
    pseudovowel = 3
    space = 4


valid_word_list = []
invalid_words = {}
for entry in dictionary:
    entry = to_monographic(entry)
    if ' ' in entry:
        invalid_words[entry] = InvalidReason.space
    elif entry[-1] in ['ʟ', 'ʀ']:
        invalid_words[entry] = InvalidReason.pseudovowel
    elif entry[-1] in ['à', 'è', 'á', 'é']:
        invalid_words[entry] = InvalidReason.diphthong
    elif entry[-1] in ['ì', 'ä']:
        invalid_words[entry] = InvalidReason.diacritic
    else:
        valid_word_list.append(entry)

print(valid_word_list)
print(invalid_words)


class GameMode(Enum):
    elimination = 1


# A list of currently running games, formatted as a dict with the following K,V:
#     K: The channel:
#     V: dict:
#         "game_mode": The game mode (see above class)
#         "players": The list of players in the game if applicable.
#         "word": The last used word.
#         "used_words": The list of previously used words.
#         "current_player": The index of the current player from the list.
games = {}


async def start_game(channel: disnake.TextChannel, game_mode: GameMode, player_list: list[disnake.User]):
    first_word = random.choice(valid_word_list)
    games[channel] = {}
    games[channel]["game_mode"] = game_mode
    games[channel]["players"] = player_list
    games[channel]["word"] = first_word
    games[channel]["used_words"] = [first_word]
    games[channel]["current_player"] = 0

    word_data = reykunyu.get_from_dictionary(from_monographic(first_word))
    embed = disnake.Embed(color=config.neutral_color,
                          title=util.i18n("wordgame.begin"),
                          description=util.i18n("wordgame.start_message") % ("Elimination", from_monographic(first_word)) +
                          "\n\n" + util.i18n("wordgame.turn") % player_list[0].id)
    try:
        embed.add_field(name=util.i18n("meaning"), value="; ".join(word_data.translate("en")))
    except AttributeError:
        print("Cannot add meaning for " + first_word)
    try:
        embed.add_field(name=util.i18n("part_of_speech"), value=word_data.part_of_speech)
    except AttributeError:
        print("Cannot add part of speech for " + first_word)
    try:
        embed.add_field(name=util.i18n("stress"),
                        value=word_data.best_pronunciation.get(capitalized=False, prefix="**", suffix="**"))
    except AttributeError:
        print("Cannot add stress for " + first_word)
    except NoPronunciationError:
        print("Cannot add stress for " + first_word)
    await channel.send(embed=embed)


class EliminationSignup(disnake.ui.View):
    def __init__(self, author: disnake.User, message: disnake.Message):
        super().__init__(timeout=3600)
        # Dict where first K is the player, V is a bool representing their readiness.
        self.players = {author: False}
        self.message = message
        self.embed_base = disnake.Embed(color=config.neutral_color,
                                        title=util.i18n("wordgame.game_starting"),
                                        description=util.i18n("wordgame.elimination_start_desc"))
        self.minimum_players = 2

    async def on_timeout(self) -> None:
        await self.message.delete()

    async def update(self):
        embed = self.embed_base.copy()
        start = True
        raw_player_list = []

        for player in self.players:
            raw_player_list.append(player)

            embed.description += "<@%s>: " % player.id
            if self.players.get(player):
                embed.description += "Ready"
            else:
                start = False
                embed.description += "Unready"
            embed.description += "\n"

        if len(raw_player_list) == 0:
            games.pop(self.message.channel)
            await self.message.delete()
        else:
            if start and len(raw_player_list) >= self.minimum_players:
                await start_game(self.message.channel, GameMode.elimination, raw_player_list)
                await self.message.delete()
            else:
                await self.message.edit(content="", embed=embed)

    @disnake.ui.button(label="Join", style=disnake.ButtonStyle.green, custom_id="join")
    async def join(self, button, inter: disnake.MessageInteraction):
        if inter.author not in self.players:
            self.players[inter.author] = False
            await inter.response.defer()
            await self.update()
        else:
            await inter.response.send_message(embed=util.errorEmbed(util.i18n("wordgame.already_joined")),
                                              ephemeral=True)

    @disnake.ui.button(label="Leave", style=disnake.ButtonStyle.red, custom_id="leave")
    async def leave(self, button, inter: disnake.MessageInteraction):
        if inter.author in self.players:
            self.players.pop(inter.author)
            await inter.response.defer()
            await self.update()
        else:
            await inter.response.send_message(embed=util.errorEmbed(util.i18n("wordgame.not_joined")), ephemeral=True)

    @disnake.ui.button(label="Toggle Ready", style=disnake.ButtonStyle.blurple, custom_id="ready")
    async def toggle_ready(self, button, inter: disnake.MessageInteraction):
        if inter.author not in self.players:
            await inter.response.send_message(embed=util.errorEmbed(util.i18n("wordgame.not_joined")), ephemeral=True)
        else:
            if self.players.get(inter.author):
                self.players[inter.author] = False
            else:
                self.players[inter.author] = True
            await inter.response.defer()
            await self.update()


def invalid_word_embed(invalid_reason: InvalidReason) -> disnake.Embed:
    reason = ""

    if invalid_reason == InvalidReason.diphthong:
        reason = util.i18n("wordgame.invalid_reason.diphthong")
    elif invalid_reason == InvalidReason.diacritic:
        reason = util.i18n("wordgame.invalid_reason.diacritic")
    elif invalid_reason == InvalidReason.pseudovowel:
        reason = util.i18n("wordgame.invalid_reason.pseudovowel")
    elif invalid_reason == InvalidReason.space:
        reason = util.i18n("wordgame.invalid_reason.space")

    return disnake.Embed(color=config.error_color, title=util.i18n("wordgame.invalid_word"), description=reason)


async def accept_word(word: str, channel: disnake.TextChannel, author_id: int):
    games[channel]["word"] = word
    games[channel]["current_player"] += 1
    current_player = games.get(channel).get("current_player")
    player_list = games.get(channel).get("players")

    if current_player >= len(player_list):
        games[channel]["current_player"] = 0
        current_player = 0

    current_player_id = player_list[current_player].id
    word_data = reykunyu.get_from_dictionary(from_monographic(word))

    embed = disnake.Embed(color=config.neutral_color,
                          title=util.i18n("wordgame.wordgame"),
                          description=
                          util.i18n("wordgame.word_said") % (author_id, from_monographic(word)) + "\n\n" +
                          util.i18n("wordgame.turn") % current_player_id)

    try:
        embed.add_field(name=util.i18n("meaning"), value="; ".join(word_data.translate("en")))
    except AttributeError:
        print("Cannot add meaning for " + word)
    try:
        embed.add_field(name=util.i18n("part_of_speech"), value=word_data.part_of_speech)
    except AttributeError:
        print("Cannot add part of speech for " + word)
    try:
        embed.add_field(name=util.i18n("stress"),
                        value=word_data.best_pronunciation.get(capitalized=False, prefix="**", suffix="**"))
    except AttributeError:
        print("Cannot add stress for " + word)
    except NoPronunciationError:
        print("Cannot add stress for " + word)

    await channel.send(embed=embed)


async def win(player: disnake.User, channel: disnake.TextChannel):
    games.pop(channel)
    await channel.send(embed=disnake.Embed(
        color=config.neutral_color,
        title=util.i18n("wordgame.game_over"),
        description=util.i18n("wordgame.winner") % player.id
    ))


class WordgameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="wordgamechannel", description="The main command for managing wordgame channels.",
                            default_member_permissions=disnake.Permissions(manage_channels=True))
    async def wordgamechannel(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @wordgamechannel.sub_command(name="enable", description="Enable the wordgame in the current channel.")
    async def enable(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(embed=enable_channel(inter.channel_id, inter.guild_id), ephemeral=True)

    @wordgamechannel.sub_command(name="disable", description="Disable the wordgame in the current channel.")
    async def disable(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(embed=disable_channel(inter.channel_id, inter.guild_id), ephemeral=True)

    @commands.slash_command(name="wordgame", description="The main command for Paytsyìp's wordgame")
    async def wordgame(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @wordgame.sub_command(name="start", description="Start a new wordgame session in the current channel.")
    async def start(self, inter: disnake.ApplicationCommandInteraction, game_mode: GameMode):
        if game_mode == GameMode.elimination.value:
            if inter.channel not in games:
                games[inter.channel] = None

                embed = disnake.Embed(color=config.neutral_color,
                                      title=util.i18n("wordgame.game_starting"),
                                      description=util.i18n(
                                          "wordgame.elimination_start_desc") + "<@%s>: Unready" % inter.author.id)

                await inter.response.send_message(embed=embed)
                msg = await inter.original_response()
                await msg.edit(view=EliminationSignup(inter.author, msg))
            else:
                await inter.response.send_message(embed=util.errorEmbed(util.i18n("wordgame.game_already_running")),
                                                  ephemeral=True)

    @wordgame.sub_command(name="stop", description="Stop the wordgame session in the current channel.")
    async def stop(self, inter: disnake.ApplicationCommandInteraction):
        if inter.channel in games and games.get(inter.channel):
            games.pop(inter.channel)
            await inter.response.send_message(embed=util.successEmbed(util.i18n("wordgame.game_stopped")))
        else:
            await inter.response.send_message(embed=util.errorEmbed(util.i18n("wordgame.no_game_running")),
                                              ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        print("\n----- New Message -----")
        if not message.author.bot and message.type != disnake.MessageType.application_command:
            print("Message is not a bot or command")
            channel = message.channel
            if channel in games:
                print("Channel is an active wordgame channel")
                game = games.get(channel)
                print("It is the message author's turn")
                content = message.content.lower()
                word = to_monographic(content)
                if word in invalid_words:
                    print("The word is invalid")
                    await channel.send(embed=invalid_word_embed(invalid_words.get(word)))
                elif word in valid_word_list:
                    if message.author == game.get("players")[game.get("current_player")]:
                        print("The word is valid")
                        if word.startswith(game.get("word")[-1]):
                            print("The word starts with the previous word's last character")
                            if game.get("game_mode") == GameMode.elimination:
                                print("The game mode is Elimination")
                                if word not in game.get("used_words"):
                                    print("The word is unused")
                                    await accept_word(word, channel, message.author.id)
                                    games[channel]["used_words"].append(word)
                                else:
                                    print("The word is used")
                                    games[channel]["players"].remove(message.author)
                                    current_player = games.get(channel).get("current_player")
                                    players = games.get(channel).get("players")
                                    await message.channel.send(embed=disnake.Embed(
                                        color=config.error_color,
                                        title=util.i18n("wordgame.wordgame"),
                                        description=util.i18n("wordgame.eliminated") % message.author.id
                                    ))
                                    if len(players) > 1:
                                        if current_player >= len(players):
                                            games[channel]["current_player"] = 0
                                            current_player = 0
                                    else:
                                        await win(game.get("players")[0], channel)
                    elif message.author not in game.get("players"):
                        await channel.send(embed=util.errorEmbed(util.i18n("wordgame.not_joined")))
                    else:
                        print("It is not the message author's turn")
                        await channel.send(embed=util.errorEmbed(util.i18n("wordgame.not_your_turn")))
