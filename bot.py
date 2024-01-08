import os
import random
import sys

if sys.version_info[0] < 3:
    sys.exit("Please Run the bot using Python 3.5 or higher")
elif sys.version_info[1] < 5:
    sys.exit("Please Run the bot using Python 3.5 or higher")
elif sys.version_info[0] > 3:
    print("Python 3 is the only officially supported version of python, be warned there may be errors.")
try:
    import disnake
    import git
except ImportError:
    if sys.platform == "linux":
        os.system("pip3 install --upgrade disnake[voice] gitpython pyyaml")
    else:
        os.system("pip install --upgrade disnake[voice] gitpython pyyaml")
    import disnake
import json
from disnake.ext import commands
import config
import sqlite3
from sqlite3 import Error

test_guilds = [715043968886505484, 715656323995271168, 771967854002176010]

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.InteractionBot(intents=intents, test_guilds=test_guilds, sync_commands_debug=True)

# Open files for lang settings
with open("lang/messages-english.json", encoding='utf-8') as f:
    english_lang = json.load(f)
with open("lang/messages-german.json", encoding='utf-8') as f:
    german_lang = json.load(f)

# Open files for help menu
with open("help-english.json", encoding='utf-8') as f:
    english_help_file = json.load(f)
with open("help-german.json", encoding='utf-8') as f:
    german_help_file = json.load(f)


def create_connection(path):
    connection = None
    try:
        connection = sqlite3.connect(path)
        print("Connection to SQLite DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")

    return connection


options_db = create_connection('options.db')
cursor = options_db.cursor()


def execute_query(connection, query):
    try:
        cursor.execute(query)
        connection.commit()
    except Error as e:
        if 'UNIQUE constraint failed:' not in str(e):
            print(f"The error '{e}' occurred")


def execute_read_query(query):
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Error as e:
        print(f"The error '{e}' occurred")


execute_query(options_db, """
CREATE TABLE IF NOT EXISTS guilds (
  id TEXT,
  PRIMARY KEY (id)
);
""")

execute_query(options_db, """
CREATE TABLE IF NOT EXISTS options (
  option TEXT NOT NULL, 
  value TEXT NOT NULL, 
  guild_id TEXT NOT NULL, 
  UNIQUE (option, guild_id),
  FOREIGN KEY (guild_id) REFERENCES guilds (id)
);
""")

execute_query(options_db, """
CREATE TABLE IF NOT EXISTS possible_values (
  possible_value TEXT NOT NULL,
  option TEXT NOT NULL, 
  PRIMARY KEY (possible_value),
  FOREIGN KEY (option) REFERENCES options (option)
);
""")

lang = {}


async def set_lang():
    for num, guild in enumerate(execute_read_query("SELECT * FROM guilds")):
        guild = guild[0]
        lang_value = execute_read_query("SELECT [value] FROM options WHERE ([option] = 'language') AND ([guild_id] = '" + guild + "')")[0][0]
        if lang_value == "English":
            lang[str(guild)] = english_lang
        elif lang_value == "German":
            lang[str(guild)] = german_lang


def get_name(id: int, guild: disnake.Guild):
    # Get user id
    user = id
    # Get the member from the user ID
    name = disnake.Guild.get_member(guild, user)
    # Get their server nickname
    name = str(name.nick)

    # If the player has no nickname
    if name == "None":
        # Get the user from the user ID
        name = bot.get_user(user)
        # Get the user's display name
        name = str(name.name)
    return name


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

    for guild in bot.guilds:
        # Create entry for guild
        execute_query(options_db, """
                                    INSERT INTO
                                      guilds (id)
                                    VALUES
                                      ('""" + str(guild.id) + """');
                                    """)
        # Create entry for language setting
        execute_query(options_db, """
                                    INSERT INTO
                                      options (option, value, guild_id)
                                    VALUES
                                      ('language','English','""" + str(guild.id) + """');
                                    """)
        # Create entry for bot_channel setting
        execute_query(options_db, """
                                    INSERT INTO
                                      options (option, value, guild_id)
                                    VALUES
                                      ('bot_channel','000000000000000000','""" + str(guild.id) + """');
                                    """)
    # Create possible values for language setting
    execute_query(options_db, """
                                        INSERT INTO
                                          possible_values (possible_value, option)
                                        VALUES
                                          ('English','language');
                                        """)
    execute_query(options_db, """
                                        INSERT INTO
                                          possible_values (possible_value, option)
                                        VALUES
                                          ('German','language');
                                        """)
    # Create possible values for bot_channel setting
    execute_query(options_db, """
                                            INSERT INTO
                                              possible_values (possible_value, option)
                                            VALUES
                                              ('ANY','bot_channel');
                                            """)

    await set_lang()


with open("cogs/fun/swears.txt", encoding='utf-8') as f:
    swears = []
    for line in f:
        swears.append(line.strip())

# @bot.event
# async def on_message(message):
#     if message.author.id == 821316706646491137:
#         await message.channel.send(random.choice(swears) + '!')


# Help command
@bot.slash_command(name="options", description="Manage server options.", guild_ids=test_guilds)
async def options(inter, action_type: str, option: str, value: str = ""):

    # Confirm the player has operator permissions, either through guild perms or through the bot operators
    is_op = False
    for perm in inter.permissions:
        if (perm == ('manage_guild', True)) or (perm == ('administrator', True)) or (inter.author.id in config.operators):
            is_op = True

    # If the player has permission
    if is_op:
        # Find results in the database for the searched option
        database_options = execute_read_query("SELECT [option], [value], [guild_id] FROM options WHERE ([guild_id] = '" + str(inter.guild_id) + "') AND ([option] = '" + option + "')")
        # Find results in the database for the possible values of the searched option
        database_possible_options = execute_read_query("SELECT [option], [possible_value] FROM possible_values WHERE ([option] = '" + option + "')")

        # If the action type is "list"
        if action_type == "list":
            # If option is "all", we know to print every option
            if option == "all":

                # Record the values of every option in the database
                all_database_options = execute_read_query("SELECT [option], [value], [guild_id] FROM options WHERE ([guild_id] = '" + str(inter.guild_id) + "')")
                # An empty string to fill later
                list_string = ""

                # Iterate over every option, and add the name and value to the string
                for database_option in all_database_options:
                    list_string += "**" + database_option[0] + "**: " + database_option[1] + "\n"

                # Send the resulting string
                await inter.response.send_message(embed=disnake.Embed(
                    title="**" + lang.get(str(inter.guild_id)).get('all_options') + "**",
                    description=list_string,
                    colour=899718), ephemeral=True)

            # Otherwise, set some text for the specified option,
            # then iterate over all possible values and add them to the string
            else:
                list_string = "**" + lang.get(str(inter.guild_id)).get('value') + "**: " + database_options[0][1] + "\n"
                list_string += "**" + lang.get(str(inter.guild_id)).get('possible_values') + "**:"
                for database_possible_option in database_possible_options:
                    list_string += "\n - " + database_possible_option[1]
                await inter.response.send_message(embed=disnake.Embed(
                    title="**" + database_options[0][0] + "**",
                    description=list_string,
                    colour=899718), ephemeral=True)

        # If the action type is "set"
        elif action_type == "set":
            # A variable to track set action success
            success = False

            # If the user has specified a value
            if value:
                # Check all possible options
                for database_possible_option in database_possible_options:
                    # If the possible value is ANY
                    if database_possible_option[1] == 'ANY':
                        # Change the option
                        execute_query(options_db, """
                                            UPDATE options
                                            SET value = '""" + value + """'
                                            WHERE ([guild_id] = '""" + str(inter.guild_id) + """')
                                            AND ([option] = '""" + option + """')
                                            """)
                        # Set success to be true
                        success = True
                        await inter.response.send_message(embed=disnake.Embed(description=lang.get(str(inter.guild_id)).get('options_set').replace('&1', option).replace('&2', value), colour=899718), ephemeral=True)

                    # If the possible value matches the value specified
                    elif value == database_possible_option[1]:
                        # Change the option
                        execute_query(options_db, """
                                            UPDATE options
                                            SET value = '""" + value + """'
                                            WHERE ([guild_id] = '""" + str(inter.guild_id) + """')
                                            AND ([option] = '""" + option + """')
                                            """)
                        # Set success to be true
                        success = True
                        # Ensure that we recalculate the language if it is changed
                        if option == 'language':
                            await set_lang()
                        await inter.response.send_message(embed=disnake.Embed(description=lang.get(str(inter.guild_id)).get('options_set').replace('&1', option).replace('&2', value),colour=899718), ephemeral=True)

                # If the the option can't be set to the value, send an error message
                if not success:
                    await inter.response.send_message(
                        embed=disnake.Embed(title=lang.get(str(inter.guild_id)).get('options_title'),
                                            description=lang.get(str(inter.guild_id)).get('options_invalid_value').replace('&1', option).replace('&2', value),
                                            colour=0xff0000), ephemeral=True)

            # If the user has NOT specified a value, send an error message
            else:
                await inter.response.send_message(
                    embed=disnake.Embed(title=lang.get(str(inter.guild_id)).get('options_title'),
                                        description=lang.get(str(inter.guild_id)).get('incorrect_usage'),
                                        colour=0xff0000), ephemeral=True)

        # If the action type is "toggle"
        elif action_type == "toggle":
            # A variable to hold whether or not the selected option is boolean
            is_bool = False

            for database_possible_option in database_possible_options:
                if (database_possible_option[1] == 'True') or (database_possible_option[1] == 'False'):
                    is_bool = True

            # If the variable is still false, the selected option is not a boolean, and we can return an error
            if not is_bool:
                await inter.response.send_message(
                    embed=disnake.Embed(title=lang.get(str(inter.guild_id)).get('options_title'),
                                        description=lang.get(str(inter.guild_id)).get('options_not_boolean').replace('&1', option),
                                        colour=0xff0000), ephemeral=True)

            # Otherwise, it is a boolean option, and we can continue
            else:
                for database_option in database_options:
                    # If value is True, set it to False
                    if database_option[1] == 'True':
                        execute_query(options_db, """
                        UPDATE options
                        SET value = 'False'
                        WHERE ([guild_id] = '""" + str(inter.guild_id) + """')
                        AND ([option] = '""" + option + """')
                        """)
                        await inter.response.send_message(embed=disnake.Embed(description=lang.get(str(inter.guild_id)).get('options_set').replace('&1', option).replace('&2', 'False'),colour=899718), ephemeral=True)
                    # Otherwise, value is False, and we can set it to True
                    else:
                        execute_query(options_db, """
                                            UPDATE options
                                            SET value = 'True'
                                            WHERE ([guild_id] = '""" + str(inter.guild_id) + """')
                                            AND ([option] = '""" + option + """')
                                            """)
                        await inter.response.send_message(embed=disnake.Embed(description=lang.get(str(inter.guild_id)).get('options_set').replace('&1', option).replace('&2', 'True'),colour=899718), ephemeral=True)

        # If the action type is anything else, it's incorrect usage and we can send an error
        else:
            await inter.response.send_message(
                embed=disnake.Embed(title=lang.get(str(inter.guild_id)).get('options_title'),
                                    description=lang.get(str(inter.guild_id)).get('incorrect_usage'),
                                    colour=0xff0000), ephemeral=True)

    # If the player does NOT have permission, send an error
    else:
        await inter.response.send_message(embed=disnake.Embed(title=lang.get(str(inter.guild_id)).get('denied'),
                                           description=lang.get(str(inter.guild_id)).get('no_access'),
                                           colour=0xff0000), ephemeral=True)


# Help command
@bot.slash_command(name="help", description="Show info about a command or list all commands.", guild_ids=test_guilds)
async def help(inter, command_name: str = ""):
    # Set the language of this help menu instance
    lang_value = execute_read_query("SELECT [value] FROM options WHERE ([option] = 'language') AND ([guild_id] = '" + str(inter.guild_id) + "')")[0][0]
    if lang_value == "English":
        help_file = english_help_file
    elif lang_value == "German":
        help_file = german_help_file

    # Empty string to reference later
    display_help = ""

    # If user has run ?help with no args, display the main help menu
    if not command_name:

        # Begin by setting the string to the instructions
        display_help = lang.get(str(inter.guild_id)).get('help_info') + "\n"

        # For each command in the help file
        for command in help_file:
            # Add this command's command name and description to the string
            display_help += "\n" + command["command"] + ": " + command["description"]

    # If there are arguments
    else:

        # Remove prefixes from beginning of arg (For more intuitive arguments)
        command_name = command_name.replace('/', '')

        # For each command in the help file
        for command in help_file:

            # Find command for argument by stripping the current command's command name of its formatting and prefix,
            # then testing if the result is equal to the argument
            if str(command["command"]).strip('**{/}**') == command_name:

                # Add command name and description
                display_help += "\n\n" + command["command"] + ": " + command["description"] + "\n"

                # Try to find aliases for command
                try:
                    # Empty list to reference later
                    alias_list = []

                    # If there are aliases, add a section for them to the string
                    if command["aliases"]:
                        display_help += "**Aliases**: "

                    # Add any aliases to alias_list
                    for alias in command["aliases"]:
                        alias_list.append(alias)

                    # Join alias_list into a string and add it to display_help
                    display_help += ', '.join(alias_list)

                    # If there are aliases, add a new line to display_help
                    if command["aliases"]:
                        display_help += "\n"

                # If there are no aliases
                except KeyError:
                    # Do nothing
                    pass

                # Add usage section and a new line
                display_help += "**Usage**: " + command["usage"] + "\n"

                # Try to find arg types for command
                try:

                    # If there is an arg_types section
                    if command["arg_types"]:
                        # Add section for them to display_help
                        display_help += "**Args**:\n"

                    # For every key in arg_types, add it's name to the string and add its value as a code block,
                    # followed by a new line
                    for key in command["arg_types"]:
                        display_help += key + ": " + "```" + command["arg_types"].get(key) + "```" + "\n"

                # If there is no arg_types section
                except KeyError:
                    # Do nothing
                    pass
                # Add an example of command usage
                display_help += "**Example**: " + command["example"]

        # If display_help has not been changed from its default (nothing was found for the args), send a warning
        if display_help == lang.get(str(inter.guild_id)).get('help_info') + "\n" or display_help == "":
            await inter.response.send_message(
                embed=disnake.Embed(title=lang.get(str(inter.guild_id)).get('help_title'),
                                    description=lang.get(str(inter.guild_id)).get('help_invalid_command').replace('&1', command_name), colour=0xff0000), ephemeral=True)

    # If display_help has been changed from its default (values were found for the args), send the finished help menu
    if not display_help == lang.get(str(inter.guild_id)).get('help_info') + "\n" and not display_help == "":
        await inter.response.send_message(embed=disnake.Embed(title=lang.get(str(inter.guild_id)).get('help_title'), description=display_help, colour=899718), ephemeral=True)


@bot.slash_command(name="info", description="Some basic info about me.", guild_ids=test_guilds)
async def info(inter):
    embed = disnake.Embed(
        title=lang.get(str(inter.guild_id)).get('info_title'),
        description=lang.get(str(inter.guild_id)).get('info_basic')
    )

    embed.add_field(name=lang.get(str(inter.guild_id)).get('info_version') + ":",value=config.version)
    embed.add_field(name=lang.get(str(inter.guild_id)).get('info_repo') + ":", value=config.repository)
    embed.add_field(name=lang.get(str(inter.guild_id)).get('info_discord') + ":", value=config.test_server_link)
    embed.add_field(name=config.discord_library + ":", value=str(disnake.version_info.major) + "." + str(disnake.version_info.minor) + "." + str(disnake.version_info.micro))

    await inter.response.send_message(embed=embed, ephemeral=True)


# Load cogs
#bot.load_extension('cogs.fun.main')
bot.load_extension('cogs.frequency.main')
#bot.load_extension('cogs.wordgame.main')

# Run bot
bot.run(config.token)
