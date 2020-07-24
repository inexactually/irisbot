import collections

import discord
import discord.ext.commands as commands


class RoleCog(commands.Cog):
    """A base class for cogs that need to manage roles.

    Override `key_for_role` to determine which roles are cached and
    what name (key) they are accessible under.
    """

    def __init__(self, bot):
        self.bot = bot
        # guild -> key -> set of roles
        self._cache = collections.defaultdict(
            lambda: collections.defaultdict(set))

    def key_for_role(self, role):
        raise NotImplementedError

    def rebuild_cache(self, guild=None):
        guilds = [guild] if guild else self.bot.guilds
        for guild in guilds:
            if guild in self._cache:
                del self._cache[guild]
            for role in guild.roles:
                self._sync_role(role)

    def get_roles(self, guild, key):
        return self._cache[guild].get(key, set())

    def get_role(self, guild, key, *, default=None):
        for role in self.get_roles(guild, key):
            return role
        return default

    def roles_by_key(self, guild):
        for key, group in self._cache[guild].items():
            for role in group:
                yield key, role

    def all_roles(self, guild):
        for group in self._cache[guild].values():
            yield from group

    def all_keys(self, guild):
        return self._cache[guild].keys()

    def _sync_role(self, role):
        key = self.key_for_role(role)
        if key:
            self._cache[role.guild][key].add(role)

    def _remove_role(self, role):
        key = self.key_for_role(role)
        if key:
            self._cache[role.guild][key].remove(role)

    @commands.Cog.listener()
    async def on_ready(self):
        self.rebuild_cache()

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        self._sync_role(role)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        self._remove_role(role)

    @commands.Cog.listener()
    async def on_guild_role_update(self, old, new):
        self._remove_role(old)
        self._sync_role(new)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        for role in guild.roles:
            self._sync_role(role)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if self._cache[guild]:
            del self._cache[guild]
