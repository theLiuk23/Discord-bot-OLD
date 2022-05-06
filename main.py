# used when running the proper bot
from discord.ext import commands
import configparser
import discord.ext
import subprocess
import platform
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


# reads an option in a *.ini file
def read_ini(config: configparser.RawConfigParser, filename: str, section: str, option: str) -> str:
    config.read(filename)
    # checks if the option exists
    if not config.sections().__contains__(section):
        print("no section specified.")
        return ""
    elif not config.options(section).__contains__(option):
        print("no option specified.")
        return ""
    return config.get(section, option)


# saves an option to a *.ini file
def save_ini(config: configparser.RawConfigParser, filename: str, section: str, option: str, value: str):
    # reads the *.ini file
    config.read(filename)
    # if section does not exist, create it
    if not config.sections().__contains__(section):
        config.add_section(section)

    config.set(section, option, value)
    with open(filename, 'w') as file:
        config.write(file)


# downloads ffmpeg if not already installed
def download_ffmpeg(kernel: str):
    try:
        # if it does not run an exception it means ffmpeg is already installed
        subprocess.check_output(['which', 'ffmpeg'])
    except subprocess.CalledProcessError as e:
        if kernel == 'Linux':
            os.system('sudo apt install ffmpeg -y')
        elif kernel == 'Windows':
            os.system('pip install ffmpeg')
        else:
            print(f'Your operating system {kernel} is not supported.')


def main():
    # saves in settings.ini, under 'os' option the os currently in use
    save_ini(config, 'settings.ini', 'variables', 'os', platform.system())
    # checks if ffmpeg is installed
    download_ffmpeg(platform.system())
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