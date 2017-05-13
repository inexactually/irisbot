import sys

import discord
from discord.ext import commands

import rolecache
import utils


ADULT_ROLE_NAME = utils.setting('AGE_ADULT_ROLE', 'Adult')
MINOR_ROLE_NAME = utils.setting('AGE_MINOR_ROLE', 'Minor')

ROLE_LOOKUP = {
    ADULT_ROLE_NAME.lower(): 'adult',
    MINOR_ROLE_NAME.lower(): 'minor'
}

def check_age_unassigned(ctx):
    cog = ctx.bot.cogs['Age']
    age_roles = set(cog.all_roles(ctx.message.server))
    for role in ctx.message.author.roles:
        if role in age_roles:
            return False
    return True


class Age(rolecache.RoleCache):
    """One-time commands to register the user as a minor or an adult.
    """

    def key_for_role(self, role):
        return ROLE_LOOKUP.get(role.name.lower())

    @commands.group(no_pm=True, invoke_without_command=True)
    @commands.check(check_age_unassigned)
    async def age(self, *, adult_or_minor : str = None):
        """Registers you as an adult or as a minor."""
        await self.bot.reply('You must specify "adult" or "minor".')

    @age.command(pass_context=True, no_pm=True)
    @commands.check(check_age_unassigned)
    async def adult(self, ctx):
        """Registers you as an adult."""
        member = ctx.message.author
        role = self.get_role(ctx.message.server, 'adult')
        await self.bot.add_roles(member, role)
        await self.bot.reply('Registered you as an adult.')

    @age.command(pass_context=True, no_pm=True)
    @commands.check(check_age_unassigned)
    async def minor(self, ctx):
        """Registers you as a minor."""
        member = ctx.message.author
        role = self.get_role(ctx.message.server, 'minor')
        await self.bot.add_roles(member, role)
        await self.bot.reply('Registered you as a minor.')

    @age.error
    @adult.error
    @minor.error
    async def age_not_reassignable(self, error, ctx):
        if utils.is_local_check_failure(error):
            message = ("You can't change your age on your own. If you just turned 18, "
                       "please ask a mod or admin to update it for you.")
            await self.bot.reply(message)
