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


class IrisContext(commands.Context):
    async def reply(self, content, *args, separator=' ', **kwargs):
        text = '{0.mention}{1}{2}'.format(self.author, separator, str(content))
        return await self.send(text, *args, **kwargs)


class Bot(commands.Bot):
    """A subclass of `discord.ext.commands.Bot` with some improvements.
    """

    async def on_message(self, message):
        ctx = await self.get_context(message, cls=IrisContext)
        await self.invoke(ctx)
