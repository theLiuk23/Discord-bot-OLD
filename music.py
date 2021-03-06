'''
Music class called from "main.py"
All the commands are in "commands.txt" and all the information about them are
in the documentation in the GitHub repository
I file called "settings.ini" is hidden from the GitHub repository because it contains a bunch of 
provate information, such as the bot token

To get access of the GitHub repository, visit https://github.com/theLiuk23/Discord-music-bot
If you have any question, write me at ldvcoding@gmail.com
'''


from urllib.error import HTTPError
from discord.ext import commands
from discord.ext import tasks
import lyricsgenius
import youtube_dl
import discord
import datetime
import main
import sys
import os


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn' }
        self.YDL_OPTIONS = {
            'format': 'bestaudio',
            'ignoreerrors':'True',
            'noplaylist': 'True',
            'quiet': 'True' }
        self.is_playing = False
        self.voice_channel = None
        self.current_song = None # music queue of index "-1" (the element that was 0 before deleting it)
        self.music_position = 0.0
        self.current_volume = 1.0
        self.music_queue = [] # music queue is a list, each element composed by a playlist (dictionary) and a voice channel
        self.log = [] # list of all the commands given in this session
        self.bot = bot


    @tasks.loop(seconds=5)
    async def check_members(self):
        '''
        it checks every 5 seconds if the bot is alone in a voice channel.
        '''
        if self.voice_channel is None:
            return
        members_count = len(self.voice_channel.channel.members)
        if members_count == 1:
            await self.disconnect_from_voice_channel()
            return

    
    @tasks.loop(minutes=10)
    async def check_is_playing(self):
        '''
        it checks every 10 minutes if the bot is not playing anymore.
        '''
        if self.voice_channel is None:
            return
        if not self.voice_channel.is_playing():
            await self.disconnect_from_voice_channel()
            return


    async def save_log(self):
        '''
        it saves the local list "log" in a txt file named "log.txt" containing all the given commands.
        '''
        maximum_lines = 1000
        filename = 'log.txt'
        with open(filename, 'a') as file:
            file.writelines(self.log)
        length = sum(1 for line in open(filename, 'r')) # gets the number of lines
        if length > maximum_lines:
            with open(filename, 'r') as file: # gets a list of lines
                data = file.read().splitlines(True)            
            with open(filename, 'w') as file: # deletes old and exceeding lines (20% of the file)
                file.writelines(data[maximum_lines:])


    async def save_volume(self):
        '''
        it saves the volume in "settings.ini" so that the bot can start again with the same volume as the last session.
        '''
        main.save_ini(main.config, 'settings.ini', 'variables', 'volume', str(self.current_volume))


    async def load_volume(self):
        '''
        it loads the volume from the last session. The float value is being read in "settings.ini"
        '''
        self.current_volume = float(main.read_ini(main.config, 'settings.ini', 'variables', 'volume'))


    async def reload_bot(self, ctx):
        '''
        if an unhandled exception is generated, the bot will try to reload.
        '''
        await ctx.send("Bot is now reloading...")
        await self.bot.close()
        os.execv(sys.executable, ['python3'] + ['main.py']) # launches from linux terminal


    async def connect_to_voice_channel(self, ctx):
        '''
        the bot connects to a voice channel. It returns a boolean whether the connection was successful.
        '''
        voice = ctx.author.voice
        if self.voice_channel is not None: # checks if the bot is already connected
            return False
        if voice is None:
            await ctx.send('Please connect to a voice channel.')
            return False
        self.voice_channel = await voice.channel.connect()
        await ctx.guild.change_voice_state(channel=self.voice_channel.channel, self_mute=False, self_deaf=True)
        return True


    async def disconnect_from_voice_channel(self):
        '''
        the bot disconnects from the voice channel. It returns a boolean whether the disconnection was successful.
        '''
        if self.voice_channel is None:
            return False
        if not self.voice_channel.is_connected():
            return False
        await self.voice_channel.disconnect()
        if len(self.log) != 0: # saves the log into a *.txt file
            await self.save_log()
        # refactors all the variables
        self.voice_channel = None
        self.current_song = None
        self.is_playing = False
        self.music_position = 0.0
        self.music_queue = []
        self.log = []
        return True


    def play_music(self, error=None):
        '''
        this function can be called from:
            the play command if the user adds a song to the music queue (and the bot is not playing anything)
            the play_music() function when the previous song ends
            the skip command (called by the user)
        '''
        if len(self.music_queue) > 0:
            song_url = self.music_queue[0][0]['source'] # so [0] means the first song, [0] means the playlist, ['source'] the value of source in the dictionary
            self.current_song = self.music_queue[0]
            self.music_queue.pop(0) # removes the first element because it is about to be played
            if self.voice_channel is None or not self.voice_channel.is_connected():
                return
            if not self.voice_channel.is_playing():
                self.voice_channel.play(discord.FFmpegPCMAudio(song_url, **self.FFMPEG_OPTIONS), after=self.play_music)
            self.voice_channel.source = discord.PCMVolumeTransformer(self.voice_channel.source, volume=self.current_volume) # transforms the volume
            self.music_position = (datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() # gets the time stamp of the playing song
            self.is_playing = True
        else:
            self.is_playing = False

    
    async def add_song_from_yt(self, ctx, *args):
        '''
        it adds to the list "music_queue" a song loaded from YouTube. Then if the bot isn't already playing, it loads "play_music" function.
        '''
        if len(args) == 0:
            await ctx.send("Write a song to play, please.")
            return
        query = " ".join(args)
        with youtube_dl.YoutubeDL(self.YDL_OPTIONS) as ydl: # gets the song info from YouTube
            try:
                info_temp = ydl.extract_info("ytsearch:%s" % query, download=False)['entries'][0]
                song_info = {'source': info_temp['formats'][0]['url'], 'title': info_temp['title'],
                             'duration': info_temp['duration'], 'channel': info_temp['channel']}
            except HTTPError:
                await ctx.send("This song is a stream or a playlist and it can't be downloaded. Try with a different query.")
                return
            except:
                await ctx.send(f'The song "{query}" can\'t be downloaded now.')
                return
        self.music_queue.append([song_info, ctx.author.voice.channel])
        await ctx.send("***{}*** added to the queue.".format(song_info['title']))
        if self.is_playing is False:
            self.play_music()


    async def add_playlist_by_name(self, ctx, playlist_name):
        '''
        it adds to the list "music_queue" some info taken by the first result on YouTube.
        '''
        songs = await self.get_songs_in_playlist_by_name(playlist_name)
        await ctx.send(f"Playlist ***{playlist_name}*** added to the queue.")
        for song in songs:
            with youtube_dl.YoutubeDL(self.YDL_OPTIONS) as ydl:
                try:
                    # temporary info
                    info_temp = ydl.extract_info("ytsearch:%s" % song, download=False)['entries'][0]
                    song_info = {'source': info_temp['formats'][0]['url'], 'title': info_temp['title'],
                                 'duration': info_temp['duration'], 'channel': info_temp['channel']}
                except HTTPError:
                    await ctx.send(
                        "This song is a stream or a playlist and it can't be downloaded. Try with a different query.")
                    return
                except:
                    await ctx.send(f'The song "{song}" can\'t be downloaded now.')
                    return
            self.music_queue.append([song_info, ctx.author.voice.channel])
            if self.is_playing is False:
                self.play_music()


    async def add_playlist_by_index(self, ctx, index):
        '''
        it adds to the list "music_queue" some info taken by the first result on YouTube.
        '''
        songs = await self.get_songs_in_playlist_by_index(index)
        await ctx.send(f"Playlist ***{(await self.get_playlists_list())[int(index) - 1]}*** added to the queue.")
        for song in songs:
            with youtube_dl.YoutubeDL(self.YDL_OPTIONS) as ydl:
                try:
                    # temporary info
                    info_temp = ydl.extract_info("ytsearch:%s" % song, download=False)['entries'][0]
                    song_info = {'source': info_temp['formats'][0]['url'], 'title': info_temp['title'],
                                 'duration': info_temp['duration'], 'channel': info_temp['channel']}
                except HTTPError:
                    await ctx.send(
                        "This song is a stream or a playlist and it can't be downloaded. Try with a different query.")
                    return
                except:
                    await ctx.send(f'The song "{song}" can\'t be downloaded now.')
                    return
            self.music_queue.append([song_info, ctx.author.voice.channel])
            if self.is_playing is False:
                self.play_music()


    async def get_songs_in_playlist_by_name(self, pl_name, ctx):
        '''
        it gets the songs' titles in a playlist from its name.
        '''
        if not os.path.exists(f'playlists/{pl_name}.txt'):
            await ctx.send(f'The requested playlist "{pl_name}" does not exist. To see a list of available playlists, type [prefix]pl.')
            return
        if pl_name is None:
            await ctx.send("Please write the name of a playlist.")
            return
        if pl_name.strip() == "":
            await ctx.send("Please write the name of a playlist.")
            return
        with open(f'playlists/{pl_name}.txt', 'r') as file:
            songs = file.readlines()
            for song in songs:
                if song.lstrip() == "":
                    songs.remove(song)
        return songs
        

    async def get_songs_in_playlist_by_index(self, index):
        '''
        it gets the songs' titles in a playlist from the index of it.
        '''
        song = (await self.get_playlists_list())[int(index) - 1]
        return await self.get_songs_in_playlist_by_name(song, None)


    async def send_np_embed(self, ctx):
        '''
        it sends an embed with a lot of information about the current playing song.
        '''
        track = self.current_song[0]
        if self.music_position is None:
            await ctx.send('I could not get the song length.')
        duration_seconds = int(track['duration'])
        time_stamp = (datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0,
                                                                                microsecond=0)).total_seconds() - self.music_position
        # converts the seconds in minutes and seconds (and percentage)
        time_stamp = (str(int(time_stamp / 60)) + " minutes and " + str(int(time_stamp % 60)) + " seconds. (" + str(
            round(time_stamp / duration_seconds * 100, 2)) + "%)")
        embed = discord.Embed(title="Now playing")
        embed.set_footer(text=f'*Requsted by {ctx.author.display_name}')
        embed.add_field(name="Track title", value=track['title'], inline=False)
        embed.add_field(name="Channel", value=track['channel'], inline=False)
        embed.add_field(name="Duration", value=str(int(duration_seconds / 60)) + " minutes and " + str(
            int(duration_seconds % 60)) + " seconds.", inline=False)
        embed.add_field(name="Already played", value=time_stamp, inline=False)
        await ctx.send(embed=embed)


    async def send_lyrics_embed(self, ctx, query=None):
        '''
        it sends an embed with the lyrics of the song (or a link to it).
        '''
        if query is None or query.lstrip() == "":
            query = self.current_song[0]['title']
        lyrics_token = main.read_ini(main.config, 'settings.ini', 'variables', 'lyrics_token')
        genius = lyricsgenius.Genius(lyrics_token)
        try:
            song = genius.search_song(title=query, get_full_info=False)
        except UnboundLocalError:
            await ctx.send(
                'I did not find any song. Try to specify manually the title as an argument of the command (e.g.=!lyrics Bella Ciao')
            return
        if song is None:
            await ctx.send(
                'I did not find any song. Try to specify manually the title as an argument of the command (e.g.=!lyrics Bella Ciao)')
            return
        lyrics = song.lyrics
        author = song.artist
        title = song.title
        image = song.song_art_image_url
        embed = discord.Embed(title=title)
        embed.set_author(name=author)
        embed.description = f'*Requsted by {ctx.author.display_name}'
        if len(lyrics) >= 2048:
            embed.add_field(name='Link',
                            value=f'Lyrics are too long for discord embeds. Here\'s a link, my dude:\n{song.url}')
        else:
            embed.set_footer(text=lyrics)
        embed.set_image(url=image)
        await ctx.send(embed=embed)


    async def save_playlist(self, ctx, playlist_name):
        '''
        it saves the title of the songs in the list "music_queue" in a text file.
        '''
        with open(f'playlists/{playlist_name}.txt', 'w') as file:
            file.write(self.current_song[0]['title'] + "\n")
            for song in self.music_queue:
                file.write(song[0]['title'] + "\n")
        await ctx.send(f'"{playlist_name}" successfully saved.')


    async def delete_playlist_by_name(self, ctx, *pl_name):
        '''
        it deletes a playlist by the name of it.
        '''
        pl_name = " ".join(pl_name).replace(" ", "_")
        if (await self.is_playlist(ctx, pl_name))[0] is False:
            await ctx.send(f'No playlist named "{pl_name}"')
            return
        try:
            os.remove(f'playlists/{pl_name}.txt')
            await ctx.send(f'Playlist {pl_name} successfully deleted.')
        except:
            await ctx.send(f'I could not delete the playlist named {pl_name}. Are you sure it does exists?')


    async def get_playlists_list(self):
        '''
        it gets a list of all the saved playlists.
        '''
        playlists_files = []
        for file in os.listdir(os.path.dirname(__file__) + '/playlists'):  # the folder of the py project
            filename = os.fsdecode(file)
            if filename.endswith('.txt'):
                playlists_files.append(filename.replace('.txt', ''))
        return playlists_files


    async def is_playlist(self, ctx, *args):
        '''
        it tells if the argument of !p command is a playlist.
        '''
        playlists_files = await self.get_playlists_list()
        song_name = " ".join(args).replace(" ", "_")
        if playlists_files.__contains__(song_name):
            return song_name
        return None


    ### LISTENERS ###
    @commands.Cog.listener()
    async def on_ready(self):
        '''
        it loads every time the bot goes online.
        It starts the 2 loops: "check_members" and "check_is_playing"
        '''
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        await self.load_volume()
        if not self.check_members.is_running():
            self.check_members.start() # checks if bot is alone on voice channel 
        if not self.check_is_playing.is_running():
            self.check_is_playing.start() # checks if bot is not playing anything for 5 minutes
        print(f"{now} - BOT IS FINALLY ONLINE!")


    @commands.Cog.listener()
    async def on_command(self, ctx):
        '''
        it loads every time a command is being written.
        it gets some info about the command and the user, and save it in the log.
        '''
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        author = ctx.author.name
        message = ctx.message.content
        info = str({'time': now, 'author': author, 'message': message})
        self.log.append(info + "\n")


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        '''
        it loads every time an error occurs. The handled errors are: \n
            CommandNotFound (discord) \n
            CommandOnCooldown (discord) \n
            DownloadError (youtube_dl) \n
            HTTPError (urllib3) \n
        if the error is unhandled, the function "reload_bot" will be called.
        '''
        if isinstance(error, commands.CommandNotFound):
            wrong_command = str(error).split('"')[1]
            prefix = main.read_ini(main.config, 'settings.ini', 'variables', 'prefix')
            await ctx.send(
                f'Command "{wrong_command}" is not available. Type {prefix}h to get a list of all the commands.')
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"You're asking for the same command too many times. Wait {error.retry_after:.2f} seconds.")
        elif isinstance(error, youtube_dl.DownloadError):
            await ctx.send('Couldn\'t download this song. ????')
        elif isinstance(error, HTTPError):
            await ctx.send('There was a problem downloading the song. Probably a temporarly error.')
        else:
            print(error)
            await ctx.send("There is a unexpected error. The bot will reload soon.")
            await self.disconnect_from_voice_channel()
            await self.reload_bot(ctx)


    ### COMMANDS ###
    ## OFFLINE ##
    @commands.command(name="offline")
    @commands.is_owner()
    async def offline(self, ctx):
        await self.disconnect_from_voice_channel()
        await ctx.send("Bot is now offline. See ya next time!")
        await self.bot.close()


    ## P ##
    @commands.cooldown(1, 5, commands.BucketType.guild) # cooldown (1 command every 5 seconds)
    @commands.command(name="p")
    async def p(self, ctx, *args):
        if len(args) <= 0:
            await ctx.send("Please write the name of the song you want to be played.")
            return
        if not await self.connect_to_voice_channel(ctx):
            return
        if args[0] == "-pl": # loads playlist
            if len(args) == 1:
                await ctx.send("Write the index of the playlist.")
                return
            await self.add_playlist_by_index(ctx, args[1])
            return
        if await self.is_playlist(ctx, *args) is not None:
            await self.add_playlist_by_name(ctx, )
            return
        await self.add_song_from_yt(ctx, *args) # loads song


    ## SKIP ##
    @commands.command(name="skip")
    async def skip(self, ctx):
        if self.voice_channel is None:
            await ctx.send("Since I am not connected to a voice channel, I am neither playing some music.")
            return
        if len(self.music_queue) <= 0:
            await self.disconnect_from_voice_channel()
            await ctx.send("There is no song in the music queue.")
            return
        self.voice_channel.stop()
        self.play_music()
        await ctx.send('Playing the next song. ????')


    ## PING ##
    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = self.bot.latency * 1000
        if latency < 200:
            await ctx.send('Pong: {} ms. ????'.format(int(latency)))
        else:
            await ctx.send('Pong: {} ms. ????'.format(int(latency)))


    ## NOW PLAYING ##
    @commands.command(name="np")
    async def now_playing(self, ctx):
        if self.voice_channel is None:
            await ctx.send("I am not connected to a voice channel at the moment.")
            return
        if not self.voice_channel.is_playing():
            await ctx.send("I am not playing anything at the moment.")
            return
        await self.send_np_embed(ctx)


    ## STOP ##
    @commands.command(name="stop")
    async def stop(self, ctx):
        await self.disconnect_from_voice_channel()
        await ctx.send("Disconnecting...")


    ## VOLUME ##
    @commands.command(name="volume")
    async def volume(self, ctx, volume=None):
        # not connected to voice channel
        if self.voice_channel is None:
            await ctx.send("Either I am connected to a voice channel or I am playing music.")
            return
        if volume is not None: # sets the volume
            if not 0 <= volume <= 200:
                await ctx.send('Volume must me set in the range of values: 0-200')
                return
            self.voice_channel.source.volume = float(volume / 100)
            self.current_volume = float(volume / 100)
            await self.save_volume()
            await ctx.send(f"Volume changed to: {volume}%.")
        else: # gets the volume
            await ctx.send(f"Volume is set to: {int(self.current_volume * 100)}%.")
            return


    ## PREFIX ##
    @commands.command(name="prefix")
    async def prefix(self, ctx, prefix: str = None):
        if prefix is None:
            await ctx.send('You need to specify a new prefix.')
            return
        if not 1 <= len(prefix) <= 3:
            await ctx.send('Prefix must be between 1 and 3 characters long.')
            return
        main.save_ini(main.config, 'settings.ini', 'variables', 'prefix', prefix)
        await ctx.send(f'Prefix successfully changed to: "{prefix}".\nReloading the bot.')
        await self.reload_bot(ctx)


    ## NEXT ##
    @commands.command(name="next")
    async def next(self, ctx):
        message_content = ""
        if self.voice_channel is None:
            await ctx.send('I am not connected to a voice channel.')
            return
        if len(self.music_queue) == 0:
            await ctx.send('There is no song in the music queue.')
            return
        for i in range(0, len(self.music_queue)):
            message_content += f"{i + 1}   -   '{self.music_queue[i][0]['title']}'\n"
        await ctx.send(message_content)


    ## PAUSE ##
    @commands.command(name="pause")
    async def pause(self, ctx):
        if self.voice_channel is None:
            await ctx.send('I am not connected to a voice channel.')
            return
        if not self.voice_channel.is_playing():
            await ctx.send('I am not playing anything at the moment.')
            return
        self.voice_channel.pause()
        await ctx.send('Music paused.')


    ## RESUME ##
    @commands.command(name="resume")
    async def resume(self, ctx):
        if self.voice_channel is None:
            await ctx.send('I am not connected to a voice channel.')
            return
        if self.voice_channel.is_playing():
            await ctx.send('I am already playing a song.')
            return
        self.voice_channel.resume()
        await ctx.send('Music resumed.')


    ## HELP ##
    @commands.command(name="h")
    async def help(self, ctx):
        message_content = ""
        with open('commands.txt', 'r') as file: # gets commands list from text file
            commands_list = file.readlines()
        for command in commands_list: # removes new lines and adds slash after every command
            command = command.rstrip("\n")
            command += "\\"
            message_content += command
        message_content = message_content[:-1] # removes exceeding slash
        message_content += "\nvisit https://github.com/theLiuk23/Music-From-YT to get more information."
        await ctx.send(f'Here is a list of the available commands:\n{message_content}')


    ## LYRICS ##
    @commands.command(name="lyrics")
    async def lyrics(self, ctx, *title):
        if self.voice_channel is None:
            await ctx.send('I am not connected to a voice channel.')
            return
        if not self.voice_channel.is_playing():
            await ctx.send('I am not playing anything at the moment.')
            return
        title = "".join(title)
        await self.send_lyrics_embed(ctx, title)


    ## PLAYLIST ##
    @commands.command(name="pl")
    async def playlist(self, ctx, *pl_name):
        if len(pl_name) != 0:
            if "--songs" in pl_name:
                pl_name = " ".join([item for item in pl_name if item!="--songs"])
                if len(pl_name) == 0:
                    await ctx.send("Write the name of a playlist.")
                    return
                songs = await self.get_songs_in_playlist_by_name(pl_name.replace(" ", "_"), ctx)
                await ctx.send(f"Here's a list of the songs in '{pl_name}':\n" + "".join(songs))
                return
            pl_name = " ".join(pl_name).replace(" ", "_")
            if len(self.music_queue) <= 1:
                await ctx.send('More than 1 song is needed to save a playlist')
                return
            if os.path.exists(f'playlists/{pl_name}.txt'):
                await ctx.send(f'A playlist named {pl_name} already exists.')
                return
            else:
                if self.voice_channel is None:
                    await ctx.send('I am not connected to a voice channel.')
                    return
                if not self.voice_channel.is_playing():
                    await ctx.send('I am not playing anything at the moment.')
                    return
                await self.save_playlist(ctx, pl_name)
        else:
            playlists = await self.get_playlists_list()
            if len(playlists) != 0:
                message_content = "Here's a list of the available playlists:\n"
                for index in range(len(playlists)):
                    message_content += f'{index + 1}  -  {playlists[index]}\n'
                await ctx.send(message_content)


    ## DELETE PLAYLIST ##
    @commands.command(name="delpl")
    async def delete_playlist(self, ctx, *pl_name):
        if len(pl_name) == 0:
            await ctx.send('Please write the name of the playlist you want to delete.')
            return
        await self.delete_playlist_by_name(ctx, *pl_name)

        
    @commands.command(name="reload")
    async def reload(self, ctx):
        await self.reload_bot(ctx)