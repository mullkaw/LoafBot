import discord
import random as rand
import os
import temperature as tmp
import re
from datetime import datetime
from discord.ext import commands

def get_token():
    with open('loafbot-token.txt', 'r') as f:
        return f.readline().strip()

TOKEN = get_token()

description = '''let's get this bread'''
bot = commands.Bot(command_prefix='!', description=description)

# maps guild IDs to respective list of servers
greetings = {}

# load list of greetings the bot uses to respond to "hello"
def load_greetings():
    global greetings

    for guild in bot.guilds:
        with open(f"server-data/{guild.name}-{guild.id}/greetings.txt", 'r') as f:
            greetings[guild.id] = [line.replace('\\n', '\n') for line in f.readlines() \
                if line.strip() and line[0] != '#']

            if len(greetings[guild.id]) == 0:
                greetings[guild.id].append("Hello there!")

        rand.shuffle(greetings[guild.id])

# TODO make it so that it makes folders on server join
@bot.event
async def on_connect():
    pass

@bot.event 
async def on_guild_join(guild):
    # TODO factor out guild preparation stuff
    dir = f"server-data/{guild.name}-{guild.id}/"

    if not os.path.isdir(dir):
        os.mkdir(dir)
        with open(dir + "greetings.txt", 'a'):
            pass
        with open(dir + "recent-greetings.txt", 'a'):
            pass

    load_greetings()

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print(datetime.now())
    print('------')

    for guild in bot.guilds:
        # name of directory for specific server
        # ends in /
        dir = f"server-data/{guild.name}-{guild.id}/"

        if not os.path.isdir(dir):
            os.mkdir(dir)
            with open(dir + "greetings.txt", 'a'):
                pass
            with open(dir + "recent-greetings.txt", 'a'):
                pass

    load_greetings()

@bot.event
async def on_message(message):
    # convert any perceivable temperatures
    await tmp.convert_message_temps(bot, message)
    
    # always be waiting for commands
    await bot.process_commands(message)

def spaces(amt : int):
    """Returns a string of a specified number of spaces"""
    return amt * ' '

@bot.command(aliases=['h'])
async def hello(ctx):
    """say hi!"""

    # the current server
    curr_guild = ctx.guild

    # list of greetings for the current server
    curr_greetings = greetings[ctx.guild.id]

    # the total number of greetings loaded
    num_greetings = len(curr_greetings)

    # a random greeting among the greetings
    message = rand.choice(curr_greetings)
    
    # the total number of recent greetings stored
    num_recent = -1

    # the maximum amount of recent greetings to store
    max_recent = int(min(50, num_greetings / 2))

    # list of recent greetings stored
    recent_lines = []

    with open(f"server-data/{curr_guild.name}-{curr_guild.id}/recent-greetings.txt", 'r') as f:
        recent_lines = [l.strip() for l in f.readlines()]
        num_recent = len(recent_lines)

        # check whether the first line of the message
        # is within the first fifty lines of recent-greetings
        # loop until it's not
        if num_greetings >= 2:
            while message.split('\n')[0].strip() in recent_lines[-max_recent:]:
                message = rand.choice(curr_greetings)

    # if there are too many recent lines
    # then reduce the file to [max_recent] many lines
    if num_recent > max_recent:
        with open(f"server-data/{curr_guild.name}-{curr_guild.id}/recent-greetings.txt", 'w') as f:
            f.writelines([l + '\n' for l in recent_lines[-max_recent:]])

    # append first line of the greeting to recents file
    # TODO append it in the same form as in the original file
    with open(f"server-data/{curr_guild.name}-{curr_guild.id}/recent-greetings.txt", 'a') as f:
        f.write(message.split('\n')[0] + '\n')

    # send the greeting as a message
    await ctx.send(message)

@bot.command(aliases=['s'])
async def send(ctx, *args):
    """Sends a quote to be used in greetings"""

    # the current server
    curr_guild = ctx.guild

    with open(f"server-data/{curr_guild.name}-{curr_guild.id}/greetings.txt", 'a') as f:
        # line to write to greetings
        line = ""

        for arg in args:
            line += arg.replace('\n', '\\n') + ' '

        f.write(line + '\n')

        await ctx.send("**received greeting!**\n" + line.replace('\\n' ,'\n').replace('/', '\\/'))

    # reload and reshuffle greetings
    load_greetings()

@bot.command()
async def add(ctx, *args):
    """Adds a list of numbers together?"""
    res = 0
    offsets = [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]

    for arg in args:
        try:
            res += int(arg) + rand.choice(offsets)
        except ValueError:
            res += rand.choice(offsets)

    await ctx.send(res)

@bot.command()
async def mult(ctx, *args):
    """Multiplies a list of numbers together?"""
    res = 1
    offsets = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]

    for arg in args:
        try:
            res *= int(arg) + rand.choice(offsets)
        except ValueError:
            pass

    await ctx.send(res)    

@bot.command()
async def da(ctx, *args):
    """don't care didn't ask plus you're ___"""

    # format string for "don't care" message
    message = '\u200B' + spaces(17) + "͏͏don't care\n" + \
        spaces(5) + ":middle_finger{tone}:" + \
        spaces(12) + ":{blond}{gender}{curly}{tone}:" + \
        spaces(12) + ":middle_finger{tone}: \ndidn't ask plus {subject} "
    
    # variables for format string
    tone = "_tone5"
    gender = "man"
    curly = True
    blond = False
    subject = "you're"

    # regular expression strings for parsing command input
    mullkaw_regex = r"(.)*[m𝑀]+(.)*[u𝓊]*(.)*[li𝓁|1]+(.)*[li𝓁|1]*(.)*[k𝓀]+(.)*[aа𝒶4]*(.)*[w𝓌]+(.)*"
    tone_regex = r"[-]{1,2}(t|tone)[1-5]"
    no_tone_regex = r"[-]{1,2}(n|no[-]?tone)"
    blond_regex = r"[-]{1,2}blond"
    man_regex = r"[-]{1,2}(m|man)"
    woman_regex = r"[-]{1,2}(w|woman)"
    curly_regex = r"[-]{1,2}(c|curly)"
    blond_regex = r"[-]{1,2}(b|blond)"
    default_hair_regex = r"[-]{1,2}(d|default)"
    you_regex = r"[-]{1,2}(y|you)"

    # loop through arguments and set format variables
    # according to the regular expressions matched
    for arg in args:
        arg = arg.lower()
        if re.match(mullkaw_regex, arg):
            message += 'a really attractive guy '
        elif re.match(tone_regex, arg):
            tone = "_tone{}".format(int(arg[-1]))
        elif re.match(no_tone_regex, arg):
            tone = ""
        elif re.match(man_regex, arg):
            gender = "man"
        elif re.match(woman_regex, arg):
            gender = "woman"
        elif re.match(curly_regex, arg):
            curly, blond = True, False
        elif re.match(blond_regex, arg):
            curly, blond = False, True
        elif re.match(default_hair_regex, arg):
            curly, blond = False, False
        elif re.match(you_regex, arg):
            subject = "you"
        else:
            message += arg + ' '
    
    # format message with format variables
    message = message.format(tone=tone, \
        gender=gender, \
        curly="_curly_haired" if curly else "", \
        blond = "blond_haired_" if blond else "", \
        subject=subject)

    # send the "dont care" string as a message
    await ctx.send(message)

bot.run(TOKEN)
