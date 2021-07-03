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
        if 'f' in temp:
            conv = (number - 32.) * 5. / 9.
            res = f"{number}°F is {round(conv, 2)}°C"
            res_list.append(res)
        elif 'c' in temp:
            conv = (number * 9. / 5.) + 32.
            res = f"{number}°C is {round(conv, 2)}°F"
            res_list.append(res)
        else:
            # F to C
            conv = (number - 32.) * 5. / 9.
            res = f"{number}°F is {round(conv, 2)}°C"
            res_list.append(res)
            # C to F
            # if the numbers are the same then only send one line
            if conv != number:
                conv = (number * 9. / 5.) + 32.
                res = f"{number}°C is {round(conv, 2)}°F"
                res_list.append(res)

    return '\n'.join(res_list)

async def convert_message_temps(bot, message):
    """Sends a message with converted temps in the same channel
    
    Converts every perceived temperature in the message into Fahrenheit and/or Celcius
    """
    channel = message.channel
    
    # make sure the bot doesn't reply to itself
    if message.author.id != bot.user.id:
        text = message.content.lower()

        # iterate through every word starting with either F or C
        # remove the word if it's not a temperature indicator
        for word in re.findall(r"(?:f|c)[a-z]*", text):
            if word not in ['f', 'fahrenheit', 'c', 'celcius']:
                text = text.replace(word, '', 1)

        # gets all preceived temperatures in the remaining string
        temps = re.findall(temp_regex, text)
        if len(temps) >= 1:
            await channel.send(get_temps_string(temps))
