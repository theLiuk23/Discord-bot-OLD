'''
Main script of the discord music bot.
The script firstly checks if the ffmpeg library is installed
Then it reads the token and the prefix from "settings.ini" (hidden from the GitHub repository)
Finally it runs the "music.py" script, where there are all the commands' listeners
N.B.=This code is written for Linux OS. It does not work properly on other operating systems.

To get access of the GitHub repository, visit https://github.com/theLiuk23/Discord-music-bot
If you have any question, write me at ldvcoding@gmail.com
'''


# used when running the proper bot
from discord.ext import commands
import configparser
import discord.ext
import subprocess
import discord
import music
import os


### initializers ###
config = configparser.RawConfigParser()
intents = discord.Intents.default()
intents.guilds = True
intents.members = True


### variables ###
# accessible from main.py
prefix = None
client = None


def read_ini(config: configparser.RawConfigParser, filename: str, section: str, option: str) -> str:
    '''
    it reads the variables stored in the hidden file "settings.ini"
    '''
    config.read(filename)
    # checks if the option exists
    if not config.sections().__contains__(section):
        print("no section specified.")
        return ""
    elif not config.options(section).__contains__(option):
        print("no option specified.")
        return ""
    return config.get(section, option)


def save_ini(config: configparser.RawConfigParser, filename: str, section: str, option: str, value: str):
    '''
    it changes the variables' values stored in the hidden file "settings.ini"
    '''
    # reads the *.ini file
    config.read(filename)
    # if section does not exist, create it
    if not config.sections().__contains__(section):
        config.add_section(section)

    config.set(section, option, value)
    with open(filename, 'w') as file:
        config.write(file)


def download_ffmpeg():
    '''
    it checks whenether ffmpeg is installed in the machine and eventually installs it
    '''
    try:
        # if it does not run an exception it means ffmpeg is already installed
        subprocess.check_output(['which', 'ffmpeg'])
    except subprocess.CalledProcessError as e:
        os.system('sudo apt install ffmpeg -y')


def main():
    download_ffmpeg()
    # lastly it runs the bot
    prefix = read_ini(config, 'settings.ini', 'variables', 'prefix')
    token = read_ini(config, 'settings.ini', 'variables', 'bot_token')
    activity = discord.Activity(type=discord.ActivityType.listening, name="music. !h")
    client = commands.Bot(command_prefix=prefix, intents=intents, activity=activity)
    client.add_cog(music.MusicCog(client))
    client.run(token, bot=True)


# prevents the script to run when imported
if __name__ == "__main__":
    main()