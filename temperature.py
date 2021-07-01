import re
from discord.ext import commands

# regex string for integers with optional decimals
num_regex = r"-?[0-9]+\.?[0-9]*"

# regex string for a temperature
temp_regex = num_regex + r"(?:[\s°]*(?:c(?:elcius)?|f(?:ahrenheit)?|degree(?:s)?\s*(?:c(?:elcius)?|f(?:ahrenheit)?)?)|°)"

def get_temps_string(temps):
    """Returns string containing all of the perceived temperatures of the given message"""
    
    # list of temperature conversions
    res_list = []

    for temp in temps:
        # match of the number string within the temperature string
        m = re.search(num_regex, temp)

        # the value of the temperature
        number = float(m.string[m.start(0):m.end(0)])

        # whether the temperature can be perceived as Celcius or Fahrenheit
        # both if not sure
        scale = 'f' if 'f' in temp else 'c' if 'c' in temp else 'fc'

        # a single temperature conversion string
        res = ""

        if 'f' in scale:
            conv = (number - 32.) * 5. / 9.
            res = f"{number}°F is {round(conv, 2)}°C"
            res_list.append(res)
        if 'c' in scale:
            conv = (number * 9. / 5.) + 32.
            res = f"{number}°C is {round(conv, 2)}°F"
            res_list.append(res)

            # if the numbers are the same then only send one line
            if number == conv:
                res_list = res_list[:-1]

    return '\n'.join(res_list)

async def convert_message_temps(bot, message):
    """Sends a message with converted temps in the same channel
    
    Converts every perceived temperature in the message into Fahrenheit and/or Celcuis
    """
    channel = message.channel
    
    # make sure the bot doesn't reply to itself
    if message.author.id != bot.user.id:
        temps = re.findall(temp_regex, message.content.lower())
        if len(temps) >= 1:
            await channel.send(get_temps_string(temps))
