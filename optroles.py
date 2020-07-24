import discord
from discord.ext import commands

from rolecog import RoleCog
import utils

ROLE_PREFIX = utils.setting('OPT_ROLE_PREFIX', 'In:').lower()


def pretty_role(role):
    name = role.name.lower()
    if name.startswith(ROLE_PREFIX):
        return name[len(ROLE_PREFIX):]
    else:
        return name


def pretty_role_list(roles, **kwargs):
    return utils.pretty_list([pretty_role(r) for r in roles], **kwargs)


def partition_roles(roles, member):
    absent, present = [], []
    for r in roles:
        if r in member.roles:
            present.append(r)
        else:
            absent.append(r)
    return absent, present


class OptRoles(RoleCog, name="Roles"):
    """Commands to allow users to assign themselves roles.
    """

    def adminhelp(self, ctx):
        desc = ("This module lets users assign and remove certain roles from "
                "themselves. Only roles starting with the prefix `{}` can be "
                "assigned this way.").format(ROLE_PREFIX)
        desc += "\n\n"
        desc += "Currently recognized opt-in roles: {}.".format(
            ', '.join('`{}`'.format(role.name)
                      for role in self.all_roles(ctx.message.guild))
        )
        return desc

    def key_for_role(self, role):
        name = role.name.lower()
        if name.startswith(ROLE_PREFIX):
            return name[len(ROLE_PREFIX):]

    @commands.command()
    async def roles(self, ctx):
        """Lists available opt-in roles.
        """
        author = ctx.author
        guild = ctx.guild
        absent, present = partition_roles(self.all_roles(guild), author)
        available = pretty_role_list(absent)
        posessed = pretty_role_list(present)

        if available and posessed:
            message = "Available roles are {}. (You're currently in {}).".format(
                available, posessed)
        elif available and not posessed:
            message = "Available roles are {}.".format(available)
        elif posessed and not available:
            message = "You're currently in all the roles ({}).".format(
                posessed)
        else:
            message = "There are no user-joinable roles at this time."
        await ctx.reply(message)

    @commands.group(invoke_without_command=True)
    async def join(self, ctx, *roles):
        """Adds roles to the user.
        """
        roles = [r[:-1] if r.endswith(',') else r for r in roles]
        found, not_found = self.parse_role_list(ctx.message.guild, roles)
        if not_found:
            await self.say_no_such_roles(ctx, not_found)
        else:
            await self.join_roles(ctx, found)

    @join.command(name='all')
    async def join_all(self, ctx):
        """Adds all opt-in roles to the user."""
        roles = self.all_roles(ctx.message.guild)
        if roles:
            await self.join_roles(ctx, roles)
        else:
            await ctx.reply("There are no user-joinable roles at this time.")

    @commands.group(invoke_without_command=True)
    async def leave(self, ctx, *roles):
        """Removes roles from the user.
        """
        found, not_found = self.parse_role_list(ctx.message.guild, roles)
        if not_found:
            await self.say_no_such_roles(ctx, not_found)
        else:
            await self.leave_roles(ctx, found)

    @leave.command(name='all')
    async def leave_all(self, ctx):
        """Removes all opt-in roles from the user."""
        roles = self.all_roles(ctx.message.guild)
        if roles:
            await self.leave_roles(ctx, roles)
        else:
            await ctx.reply("There are no user-joinable roles at this time.")

    async def say_no_such_roles(self, ctx, names):
        message = "Sorry, there isn't any role named {}."
        await ctx.reply(message.format(utils.pretty_list(names, conjunction='or')))

    def parse_role_list(self, guild, role_names):
        found = []
        not_found = []
        for name in role_names:
            role = self.get_role(guild, name.lower())
            if role:
                found.append(role)
            else:
                not_found.append(name)
        return found, not_found

    async def join_roles(self, ctx, roles):
        user = ctx.message.author
        absent, present = partition_roles(roles, user)
        if absent:
            await user.add_roles(*absent)
            added_list = pretty_role_list(absent)
            already_list = pretty_role_list(present)
            message = "Added you to role {}."
            if present:
                message += " (You're already in {}.)"
            await ctx.reply(message.format(added_list, already_list))
        else:
            await ctx.reply("You're already in all of those roles.")

    async def leave_roles(self, ctx, roles):
        user = ctx.message.author
        absent, present = partition_roles(roles, user)
        if present:
            await user.remove_roles(*present)
            removed_list = pretty_role_list(present)
            not_in_list = pretty_role_list(absent, conjunction='or')
            message = "Removed you from role {}."
            if absent:
                message += " (You weren't in {} in the first place.)"
            await ctx.reply(message.format(removed_list, not_in_list))
        else:
            await ctx.reply("You aren't in any of those roles.")
