import re

import discord
from discord.ext import commands

from rolecog import RoleCog
import utils

ROLE_PREFIX = utils.setting('AUTO_ROLE_PREFIX', '(Auto)')
ROLE_REGEX = re.compile(re.escape(ROLE_PREFIX) +
                        r' *([^ ].+[^ ] *(\+ *[^ ].+[^ ])*)', re.I)


class AutoRoles(RoleCog, name='Auto Roles'):
    def key_for_role(self, role):
        name = role.name.lower()
        m = ROLE_REGEX.fullmatch(name)
        if m:
            role_names = tuple(part.strip() for part in m.group(1).split('+'))
            return role_names

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._processing = set()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def autoroles(self, ctx):
        """Apply automatic roles retroactively. (admin only)

        You should only have to do this once. Auto roles should apply
        automatically whenever roles change once the bot is online.
        """
        fixed = 0
        for member in ctx.message.guild.members:
            changed = await self.autorole_member(member)
            fixed += 1 if changed else 0
        message = "Updated roles on {} users."
        await ctx.reply(message.format(fixed))

    async def autorole_member(self, member):
        self._processing.add(member.id)
        role_names = set(role.name.lower() for role in member.roles)
        to_remove, to_add = [], []
        for (req1, req2), role in self.roles_by_key(member.guild):
            if req1 in role_names and req2 in role_names:
                to_add.append(role)
            elif role in member.roles:
                to_remove.append(role)

        changed = False
        if to_add or to_remove:
            updated_roles = (set(member.roles) - set(to_remove)) | set(to_add)
            await member.edit(roles=list(updated_roles))
            changed = True

        self._processing.remove(member.id)
        return changed

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.id in self._processing:
            return
        if before.roles == after.roles:
            return
        await self.autorole_member(after)

    def adminhelp(self, ctx):
        desc = ("This module automatically assigns and removes a role based on "
                "the other roles of a user. It can be used to create channels "
                "only visible to users who have *several* particular roles.")
        desc += '\n\n'
        desc += ("To be automatically assigned, a role should have a name that "
                 "consists of the prefix `{0}` followed by two or more role names "
                 "separated with `+` signs. For instance, a role named "
                 "`{0} Cool People + adults` will be applied to users with both "
                 "the `cool people` role and the `adults` role.").format(ROLE_PREFIX)
        desc += '\n\n'
        desc += "Currently recognized auto roles: {}.".format(
            utils.pretty_list(['`{}`'.format(role.name) for role in self.all_roles(ctx.message.guild)],
                              bold=False, empty='none')
        )
        return desc
