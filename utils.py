import aiohttp
import inspect
import io

import discord
from discord.ext import commands

import settings

def setting(name, default):
    return getattr(settings, name, default)

def pretty_list(names, bold=True, conjunction='and', empty=''):
    names = list(names)
    if not names:
        return empty

    if bold:
        names = ['**{}**'.format(name) for name in names]
    sep = ' ' + conjunction if conjunction else ''

    if len(names) == 1:
        return names[0]
    elif len(names) == 2:
        return '{}{} {}'.format(names[0], sep, names[1])
    else:
        return '{},{} {}'.format(', '.join(names[:-1]), sep, names[-1])

def is_local_check_failure(error):
    """This horrible hack lets a command error handler figure out if the
    error originates from the command's own checks, rather than a
    global check or some other sort of error.
    """
    if isinstance(error, commands.CheckFailure):
        if error.args:
            return "check functions for command" in error.args[0]

# Copied from discord.ext.commands.bot.py. We need this because
# there's no way to override the formatting of the defualt Bot.reply.
def bot_get_variable(name):
    stack = inspect.stack()
    try:
        for frames in stack:
            try:
                frame = frames[0]
                current_locals = frame.f_locals
                if name in current_locals:
                    return current_locals[name]
            finally:
                del frame
    finally:
        del stack

class Bot(commands.Bot):
    """A subclass of `discord.ext.commands.Bot` with some improvements.
    """
    async def reply(self, content, *args, separator=' ', **kwargs):
        # Now with custom separator support
        author = bot_get_variable('_internal_author')
        text = '{0.mention}{1}{2}'.format(author, separator, str(content))
        return await self.say(text, *args, **kwargs)

    async def send_file(self, destination, fp, *, filename=None, content=None, embed=None, tts=False):
        # Now with embed support
        channel_id, guild_id = await self._resolve_destination(destination)
        if embed is not None:
            embed = embed.to_dict()

        try:
            with open(fp, 'rb') as f:
                buffer = io.BytesIO(f.read())
                if filename is None:
                    _, filename = path_split(fp)
        except TypeError:
            buffer = fp

        content = str(content) if content is not None else None
        data = await self.http.send_file(channel_id, buffer, guild_id=guild_id,
                                    filename=filename, content=content, embed=embed, tts=tts)
        channel = self.get_channel(data.get('channel_id'))
        message = self.connection._create_message(channel=channel, **data)
        return message
