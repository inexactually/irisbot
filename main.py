import collections
import re
import sys
import traceback

import discord
from discord.ext import commands

import admintools
import age
import autoroles
import colors
import config
import formatter
import optroles
import utils


CHANNEL_WHITELIST = utils.setting('BOT_CHANNEL_WHITELIST', [])
CHANNEL_BLACKLIST = utils.setting('BOT_CHANNEL_BLACKLIST', [])
CHANNEL_REGEX     = utils.setting('BOT_CHANNEL_REGEX', r'^bots?($|[-_].*)')
ROLE_WHITELIST    = [r.lower() for r in utils.setting('BOT_ROLE_WHITELIST', [])]
ROLE_BLACKLIST    = [r.lower() for r in utils.setting('BOT_ROLE_BLACKLIST', [])]
SUPERUSER_ROLES   = [r.lower() for r in utils.setting('BOT_SUPERUSER_ROLES', [])]

async def adminhelp(ctx, *, category : str =None):
    """Gives admin-relevant details about this bot.
    """
    bot = ctx.bot
    categories = {name.lower(): cog
                  for name, cog in bot.cogs.items()
                  if hasattr(cog, 'adminhelp')}

    if not category:
        message = ("Select a module to see admin-relevant information about it. "
                   "Available categories are: {}.")
        await bot.reply(message.format(utils.pretty_list(categories, empty='none')))
        return

    cog = categories.get(category.lower())
    if not cog:
        await bot.say('No admin-specific help for "{}".'.format(category))
    else:
        await bot.say(cog.adminhelp(ctx))


class Irisbot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='?',
                         description='Self-service role and color assignment.',
                         formatter=formatter.FancyFormatter())
        self._help_text = 'say ?help in #bot-'

        # This is scary but it seems to be needed to get a cog-less command.
        self.command(no_pm=True, pass_context=True, name="adminhelp")(
            commands.has_permissions(administrator=True)(adminhelp))

        self.add_check(self.is_allowed)
        self.add_cog(admintools.AdminTools(self))
        self.add_cog(age.Age(self))
        self.add_cog(autoroles.AutoRoles(self))
        self.add_cog(colors.Colors(self))
        self.add_cog(optroles.OptRoles(self))

    def check_superuser(self, ctx):
        return any(r.name.lower() in SUPERUSER_ROLES
                   for r in ctx.message.author.roles)

    def check_channel(self, ctx):
        name = ctx.message.channel.name
        if CHANNEL_WHITELIST:
            return name in CHANNEL_WHITELIST
        if name in CHANNEL_BLACKLIST:
            return False
        if CHANNEL_REGEX:
            return re.match(CHANNEL_REGEX, name)
        return True

    def check_roles(self, ctx):
        names = [role.name.lower() for role in ctx.message.author.roles]
        if ROLE_WHITELIST:
            return any(name in ROLE_WHITELIST for name in names)
        if ROLE_BLACKLIST:
            return not any(name in ROLE_BLACKLIST for name in names)
        return True

    def is_allowed(self, ctx):
        if self.check_superuser(ctx):
            return True
        return self.check_channel(ctx) and self.check_roles(ctx)

    def oauth2_url(self):
        wanted_permissions = discord.Permissions.none()
        wanted_permissions.update(
            read_message=True,
            send_messages=True,
            change_nickname=True,
            manage_roles=True,
            ban_members=True,
        )
        url = 'https://discordapp.com/api/oauth2/authorize?client_id={}&scope=bot&permissions={}'
        return url.format(self.user.id, wanted_permissions.value)

    async def on_ready(self):
        print('Logged in as:\n  {0} (ID: {0.id})'.format(self.user))
        if self.servers:
            print('Currently in {} server(s):'.format(len(self.servers)))
            for server in self.servers:
                print('  ' + server.name)
        print('To add this bot to a server, visit:')
        print('  ' + self.oauth2_url())
        print()
        await bot.change_presence(game=discord.Game(name=self._help_text))

    async def on_command_error(self, exception, context):
        if isinstance(exception, commands.CheckFailure):
            return

        print('Ignoring exception in command {}'.format(context.command), file=sys.stderr)
        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)

    async def reply(self, content, *args, **kwargs):
        author = utils.bot_get_variable('_internal_author')
        text = '{0.mention} {1}'.format(author, str(content))
        return await self.say(text, *args, **kwargs)


if __name__ == '__main__':
    bot = Irisbot()
    bot.run(config.TOKEN)

