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
