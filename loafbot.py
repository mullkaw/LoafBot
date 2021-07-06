# TODO add configurable settings folder for each server
# TODO add control room so i can talk through the bot and configure other servers in my own server

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

# regex used to detect when --quiet flag was passed
quiet_regex = r"[-]{1,2}(?:q|quiet)"

description = '''let's get this bread'''
bot = commands.Bot(command_prefix='!', description=description)

# maps guild IDs to respective list of servers
greetings = {}

def prepare_guild(guild):
    """Creates files and folders corresponding to a server if not already there
    
    For use in storing greetings and other things
    """

    dir = f"server-data/{guild.name}-{guild.id}/"

    if not os.path.isdir(dir):
        os.mkdir(dir)
        with open(dir + "greetings.txt", 'a'):
            pass
        with open(dir + "recent-greetings.txt", 'a'):
            pass

def guild_path(guild):
    """Returns the path to this server's data folder
    
    Path ends in a forward slash
    """

    return f"server-data/{guild.name}-{guild.id}/"

def load_greetings():
    """Loads the lists of greetings the bot uses to respond to "hello"

    Does this for each server the bot is connected to
    """
    global greetings

    for guild in bot.guilds:
        with open(f"server-data/{guild.name}-{guild.id}/greetings.txt", 'r') as f:
            greetings[guild.id] = [line.replace('\\n', '\n') for line in f.readlines() \
                if line.strip() and line[0] != '#']

            if len(greetings[guild.id]) == 0:
                greetings[guild.id].append("Hello there!")

        rand.shuffle(greetings[guild.id])

@bot.event
async def on_connect():
    print('Connected')

@bot.event 
async def on_guild_join(guild):
    prepare_guild(guild)
    load_greetings()

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print(datetime.now())
    print('------')

    for guild in bot.guilds:
        prepare_guild(guild)

    load_greetings()

@bot.event
async def on_message(message):
    # convert any perceivable temperatures
    await tmp.convert_message_temps(bot, message)
    
    # check if user said either "pedro" or "juan" and send image accordingly
    if message.author.id != bot.user.id:
        if "pedro" in message.content.lower():
            await message.channel.send(file=discord.File('assets/pedro.jpg'))

        if "juan" in message.content.lower():
            await message.channel.send(file=discord.File('assets/juan.jpg'))

    # if message.author.id == bot.user.id:
    #     for url in [a.url for a in message.attachments]:
    #         await message.channel.send(url)

    # always be waiting for commands
    await bot.process_commands(message)


async def get_quiet(ctx, args):
    """Returns whether quiet flag was an argument,
    and removes it from argument list if it's there
    """

    quiet = False
    loc_args = list(args)
    args = list(args)

    for arg in loc_args:
        if re.match(quiet_regex, arg):
            quiet = True
            await ctx.message.delete()
            args.remove(arg)

    return quiet, tuple(args)

def spaces(amt : int):
    """Returns a string of a specified number of spaces"""
    return amt * ' '

@bot.command(aliases=['h'])
async def hello(ctx, *args):
    """say hi!"""

    # whether or not to execute this command quietly
    _, args = await get_quiet(ctx, args)

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

    with open(f"{guild_path(curr_guild)}recent-greetings.txt", 'r') as f:
        recent_lines = [l.strip() for l in f.readlines()]
        num_recent = len(recent_lines)

        # check whether the first line of the message
        # is within the first fifty lines of recent-greetings
        # loop until it's not
        if num_greetings >= 2:
            # filters out the recent greetings from the current greetings
            for line in recent_lines[-max_recent:]:
                if message.split('\n')[0].strip() == line:
                    curr_greetings.remove(message)
                    message = rand.choice(curr_greetings)

    # if there are too many recent lines
    # then reduce the file to [max_recent] many lines
    if num_recent > max_recent:
        with open(f"{guild_path(curr_guild)}recent-greetings.txt", 'w') as f:
            f.writelines([l + '\n' for l in recent_lines[-max_recent:]])

    # append first line of the greeting to recents file
    # TODO append it in the same form as in the original file
    with open(f"{guild_path(curr_guild)}recent-greetings.txt", 'a') as f:
        f.write(message.split('\n')[0] + '\n')

    # send the greeting as a message
    await ctx.send(message)

@bot.command(aliases=['s'])
async def send(ctx, *args):
    """Sends a quote to be used in greetings"""

    # whether or not to execute this command quietly
    quiet, args = await get_quiet(ctx, args)

    # the current server
    curr_guild = ctx.guild

    with open(f"{guild_path(curr_guild)}greetings.txt", 'a') as f:
        # line to write to greetings
        line = ""

        # remove newlines for storage purposes
        for arg in args:
            line += arg.replace('\n', '\\n') + ' '

        # only add message if it's not just whitespace
        if len(re.sub(r"\s+", '', line)) >= 1:
            f.write(line + '\n')
            if not quiet:
                await ctx.send("**received greeting!**\n" + line.replace('\\n' ,'\n').replace('/', '\\/'))
        else:
            await ctx.send("**no greeting sent**\n")

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

    # whether or not to execute this command quietly
    _, args = await get_quiet(ctx, args)

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

async def upload_video(ctx, link, quiet):
    """Uploads video at the specified link to the specified context
    
    Sends message "Unable to download video" if youtube-dl fails
    """
    # path for the video to be downloaded
    video_path = '.temp/video.mp4'

    # remove existing video.mp4 if it's already there
    if os.path.isfile(video_path):
        os.remove(video_path)

    options = "--format mp4 --no-playlist --max-filesize 8m"

    exit_code = os.system(f"youtube-dl {options} {link} --output {video_path}")

    if exit_code == 0 and os.path.isfile(video_path):
        # the message that the current message replied to
        # None if it did not reply to a message
        replied_message = ctx.message.reference

        # reply to the replied message if it's there
        # otherwise reply to the current message if it's there
        # otherwise reply to no message
        if replied_message:
            msg = await ctx.fetch_message(replied_message.message_id)
            await msg.reply(file=discord.File(video_path), mention_author=False)
        elif not quiet:
            await ctx.reply(file=discord.File(video_path), mention_author=False)
        else:
            await ctx.send(file=discord.File(video_path))

    else:
        await ctx.send("Unable to download video")

    # remove existing video.mp4 if it's still there
    if os.path.isfile(video_path):
        os.remove(video_path)

@bot.command()
async def vdl(ctx, *args):
    """Downloads a video using a provided internet link"""

    # whether or not to execute this command quietly
    quiet, args = await get_quiet(ctx, args)

    # create .temp directory if not there already
    if not os.path.isdir(".temp"):
        os.mkdir(".temp")

    # TODO maybe find a way to do this in the background 
    # so that other commands can be run in the meantime
    for arg in args:
        await upload_video(ctx, arg, quiet)

    # remove .temp directory if it's still there
    if not os.path.isdir(".temp"):
        os.rmdir(".temp")

bot.run(TOKEN)
