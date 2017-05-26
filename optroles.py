import discord
from discord.ext import commands

import rolecache
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

class OptRoles(rolecache.RoleCache):
    """Commands to allow users to assign themselves roles.
    """

    def adminhelp(self, ctx):
        desc = ("This module lets users assign and remove certain roles from "
                "themselves. Only roles starting with the prefix `{}` can be "
                "assigned this way.").format(ROLE_PREFIX)
        desc += "\n\n"
        desc += "Currently recognized opt-in roles: {}.".format(
            ', '.join('`{}`'.format(role.name) for role in self.all_roles(ctx.message.server))
        )
        return desc

    def key_for_role(self, role):
        name = role.name.lower()
        if name.startswith(ROLE_PREFIX):
            return name[len(ROLE_PREFIX):]

    @commands.command(pass_context=True, no_pm=True)
    async def roles(self, ctx):
        """Lists available opt-in roles.
        """
        user = ctx.message.author
        server = ctx.message.server
        absent, present = partition_roles(self.all_roles(server), user)
        available = pretty_role_list(absent)
        posessed  = pretty_role_list(present)

        if available and posessed:
            message = "Available roles are {}. (You're currently in {}).".format(available, posessed)
        elif available and not posessed:
            message = "Available roles are {}.".format(available)
        elif posessed and not available:
            message = "You're currently in all the roles ({}).".format(posessed)
        else:
            message = "There are no user-joinable roles at this time."
        await self.bot.reply(message)

    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    async def join(self, ctx, *roles):
        """Adds roles to the user.
        """
        roles = [r[:-1] if r.endswith(',') else r for r in roles]
        found, not_found = self.parse_role_list(ctx.message.server, roles)
        if not_found:
            await self.say_no_such_roles(not_found)
        else:
            await self.join_roles(ctx, found)

    @join.command(name='all', pass_context=True, no_pm=True)
    async def join_all(self, ctx):
        """Adds all opt-in roles to the user."""
        roles = self.all_roles(ctx.message.server)
        if roles:
            await self.join_roles(ctx, roles)
        else:
            await self.bot.reply("There are no user-joinable roles at this time.")

    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    async def leave(self, ctx, *roles):
        """Removes roles from the user.
        """
        found, not_found = self.parse_role_list(ctx.message.server, roles)
        if not_found:
            await self.say_no_such_roles(not_found)
        else:
            await self.leave_roles(ctx, found)

    @leave.command(name='all', pass_context=True, no_pm=True)
    async def leave_all(self, ctx):
        """Removes all opt-in roles from the user."""
        roles = self.all_roles(ctx.message.server)
        if roles:
            await self.leave_roles(ctx, roles)
        else:
            await self.bot.reply("There are no user-joinable roles at this time.")

    async def say_no_such_roles(self, names):
        message = "Sorry, there isn't any role named {}."
        await self.bot.reply(message.format(utils.pretty_list(names, conjunction='or')))

    def parse_role_list(self, server, role_names):
        found = []
        not_found = []
        for name in role_names:
            role = self.get_role(server, name.lower())
            if role:
                found.append(role)
            else:
                not_found.append(name)
        return found, not_found

    async def join_roles(self, ctx, roles):
        user = ctx.message.author
        absent, present = partition_roles(roles, user)
        if absent:
            await self.bot.add_roles(user, *absent)
            added_list = pretty_role_list(absent)
            already_list = pretty_role_list(present)
            message = "Added you to role {}."
            if present:
                message += " (You're already in {}.)"
            await self.bot.reply(message.format(added_list, already_list))
        else:
            await self.bot.reply("You're already in all of those roles.")

    async def leave_roles(self, ctx, roles):
        user = ctx.message.author
        absent, present = partition_roles(roles, user)
        if present:
            await self.bot.remove_roles(user, *present)
            removed_list = pretty_role_list(present)
            not_in_list = pretty_role_list(absent, conjunction='or')
            message = "Removed you from role {}."
            if absent:
                message += " (You weren't in {} in the first place.)"
            await self.bot.reply(message.format(removed_list, not_in_list))
        else:
            await self.bot.reply("You aren't in any of those roles.")
