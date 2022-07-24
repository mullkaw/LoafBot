# TODO add configurable settings folder for each server
# TODO add control room so i can talk through the bot and configure other servers in my own server

import discord
import random as rand
import os
import temperature as tmp
import re
from datetime import datetime
from discord.ext import commands
from importlib import import_module
from subprocess import run, CalledProcessError

from server_data import *

def get_token():
    with open('loafbot-token.txt', 'r') as f:
        return f.readline().strip()

TOKEN = get_token()

# regex used to detect when --quiet flag was passed
quiet_regex = r"[-]{1,2}(?:q|quiet)"

intents = discord.Intents.all()
flags = discord.MemberCacheFlags.all()

description = '''let's get this bread'''
bot = commands.Bot(command_prefix='!', description=description, intents=intents, member_cache_flags=flags)

# maps guild IDs to respective list of servers
greetings = {}

def prepare_guild(guild):
    """Creates files and folders corresponding to a server if not already there
    
    For use in storing greetings and other things
    """

    dir = f"server_data/{guild.name}-{guild.id}/"

    if not os.path.isdir(dir):
        os.mkdir(dir)
        with open(dir + "greetings.txt", 'a'):
            pass
        with open(dir + "recent-greetings.txt", 'a'):
            pass
        with open(dir + "__init__.py", 'a'):
            pass
        with open(dir + "server_code.py", 'a'):
            pass

def guild_path(guild):
    """Returns the path to this server's data folder
    
    Path ends in a forward slash
    """

    return f"server_data/{guild.name}-{guild.id}/"

def load_greetings():
    """Loads the lists of greetings the bot uses to respond to "hello"

    Does this for each server the bot is connected to
    """
    global greetings

    for guild in bot.guilds:
        with open(f"server_data/{guild.name}-{guild.id}/greetings.txt", 'r') as f:
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
async def on_guild_update(before, after):
    # change the server_data folder name if guild changed name
    id = after.id
    name_old, name_new = before.name, after.name

    if name_old != name_new:
        old_folder = f'{name_old}-{id}'
        new_folder = f'{name_new}-{id}'

        print(old_folder, new_folder)

        if old_folder in os.listdir('server_data'):
            print('here')
            os.rename(f'server_data/{old_folder}', f'server_data/{new_folder}')

@bot.event
async def on_message(message):
    if not bot.is_ready():
        return

    # convert any perceivable temperatures
    await tmp.convert_message_temps(bot, message)

    # open the server-specific code
    pkg_name = 'server_data.' + guild_path(message.guild).split('/')[1] + '.server_code'
    server_code = import_module(pkg_name)

    try:
        await server_code.on_message(message, bot)
    except AttributeError:
        print('this server does not have an on_message function')

    # always be waiting for commands
    await bot.process_commands(message)


async def get_quiet(ctx, args):
    """Returns whether quiet flag was an argument,
    and removes it from argument list if it's there
    """

    quiet = False
    loc_args = list(args)
    args = list(args)

    if len(loc_args) == 0:
        return False, ()

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
    max_recent = int(min(500, num_greetings / 2))

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
    # TODO fix server rename issue
    with open(f"{guild_path(curr_guild)}recent-greetings.txt", 'a') as f:
        f.write(message.split('\n')[0] + '\n')

    # send the greeting as a message
    await ctx.send(message)

@bot.command(aliases=['s'])
async def send(ctx):
    """Sends a quote to be used in greetings"""

    # the current server
    curr_guild = ctx.guild

    # line to write to greetings
    line = ""

    # remove newlines for storage purposes
    command_pattern = r'\!s(?:end)?(?:\s)+'
    text = ctx.message.content
    m = re.match(command_pattern, text)
    line = text[m.span()[1]:].replace('\n', '\\n') if m else ''

    # add URLs for message attachmens
    for attachment in ctx.message.attachments:
        line = line + '\n' if line != "" else line
        line += attachment.url + '\n'

    if line.endswith('\n'):
        line = line.strip()

    # only add message if it's not just whitespace
    if len(re.sub(r"\s+", '', line)) >= 1:        
        with open(f"{guild_path(curr_guild)}greetings.txt", 'r') as f:
            lines = f.readlines()

        # check if line is already in file
        if f'{line}\n' not in lines:
            with open(f"{guild_path(curr_guild)}greetings.txt", 'a') as f:
                f.write(line + '\n')

            # send response message if no quiet flag is present
            try:
                repsonse_text = "**received greeting!**\n" + line.replace('\\n' ,'\n').replace('/', '\\/')
                await ctx.send(repsonse_text)
            except discord.HTTPException:
                repsonse_text = "**received greeting!**\n"
                await ctx.send(repsonse_text)
        else:
            repsonse_text = "Greeting is already present"
            await ctx.send(repsonse_text)

    else:
        await ctx.send("**no greeting sent**\n")

    # reload and reshuffle greetings
    load_greetings()

@bot.command(aliases=['c'])
async def count(ctx, *args):
    """Returns a count of how many greetings are in this server"""

    # whether or not to execute this command quietly
    _, args = await get_quiet(ctx, args)

    # list of greetings for the current server
    curr_greetings = greetings[ctx.guild.id]

    # the total number of greetings loaded
    num_greetings = len(curr_greetings)

    await ctx.send(f"**{num_greetings}** greetings")


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

async def upload_video(ctx, link, quiet, aspect='video', format='mp4'):
    """Uploads video at the specified link to the specified context
    
    Sends message "Unable to download video" if youtube-dl fails
    """
    # path for the video to be downloaded
    video_path = f'.temp/{aspect}.{format}'

    # remove existing video.mp4 if it's already there
    if os.path.isfile(video_path):
        os.remove(video_path)

    options = f"--no-playlist --max-filesize 8m"

    if aspect == 'video':
        options += f" --format {format}"
    elif aspect == 'audio':
        options += f" --extract-audio --audio-format {format}"

    command = f"youtube-dl {options} {link} --output {video_path}"
    run(command.split()).check_returncode()

    if os.path.isfile(video_path):
        # the message that the current message replied to
        # None if it did not reply to a message
        replied_message = ctx.message.reference

        # removes video embed on current message
        # if quiet then the message is no longer there
        if not quiet:
            await ctx.message.edit(suppress=True)

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
        await ctx.send(f"Unable to download {aspect}")

    # remove existing video.mp4 if it's still there
    if os.path.isfile(video_path):
        os.remove(video_path)

    # remove temp directory if it's still there
    if os.path.isdir('.temp'):
        os.rmdir('.temp')

@bot.command()
async def vdl(ctx, *args):
    """Downloads a video using a provided internet link"""

    # list of audio formats supported by youtube-dl
    audio_formats = ["aac", "flac", "mp3", "m4a", "opus", "vorbis", "wav"]

    # whether or not to execute this command quietly
    quiet, args = await get_quiet(ctx, args)

    audio_format = None

    # create .temp directory if not there already
    if not os.path.isdir(".temp"):
        os.mkdir(".temp")

    # TODO maybe find a way to do this in the background 
    # so that other commands can be run in the meantime
    for arg in args:
        # check to see if the link is between angle brackets
        m = re.match(r"<(?P<link>(?:.)*)>", arg)
        arg = m.group('link') if m else arg

        m = re.match(r"[-]{1,2}(?P<audio_format>(?:\S)*)", arg)
        if m and m.group('audio_format') in audio_formats:
            audio_format = m.group('audio_format')
        elif audio_format:
            await upload_video(ctx, arg, quiet, aspect='audio', format=audio_format)
        else:
            await upload_video(ctx, arg, quiet)

    # remove .temp directory if it's still there
    if os.path.isdir(".temp"):
        os.rmdir(".temp")

@bot.command()
async def adl(ctx, *args):
    """Downloads audio using a provided internet link"""
    await vdl(ctx, '-mp3', *args)

@bot.command()
async def gif(ctx, *args):
    """Convert images into gifs"""

    # whether or not to execute this command quietly
    quiet, args = await get_quiet(ctx, args)

    # the message that the current message replied to
    # None if it did not reply to a message
    replied_links = []
    if ctx.message.reference:
        replied_message = await ctx.fetch_message(ctx.message.reference.message_id)
        replied_urls = [attachment.url for attachment in replied_message.attachments]
        replied_links.extend(replied_urls)

    links = [attachment.url for attachment in ctx.message.attachments] + list(args) + replied_links

    # create .temp directory if not there already
    if not os.path.isdir(".temp"):
        os.mkdir(".temp")

    file_name = 'file'
    file_path = f'.temp/{file_name}'
    file_path_png = f'.temp/{file_name}.png'
    gif_path = '.temp/gif.gif'

    for link in links:
        # download attachment from link
        command = ['wget', '--output-document', file_path, link]
        run(command).check_returncode()

        # convert downloaded image to png
        command = ['convert', file_path, file_path_png]
        run(command).check_returncode()

        # convert downloaded image into gif
        command = ['gifski', file_path_png, file_path_png, '--output', gif_path]
        run(command).check_returncode()

        if not quiet:
            await ctx.reply(file=discord.File(gif_path), mention_author=False)
        else:
            await ctx.send(file=discord.File(gif_path))

        # remove files from temp directory
        os.remove(file_path)
        os.remove(file_path_png)
        os.remove(gif_path)


    # remove .temp directory if it's still there
    if os.path.isdir(".temp"):
        os.rmdir(".temp")

bot.run(TOKEN)
