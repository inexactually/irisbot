import collections

import discord

class RoleCache:
    """A base class for cogs that need to manage roles.

    Override `key_for_role` to determine which roles are cached and
    what name (key) they are accessible under.
    """
    def __init__(self, bot):
        self.bot = bot
        # server -> key -> set of roles
        self._cache = collections.defaultdict(lambda: collections.defaultdict(set))

    def key_for_role(self, role):
        return None

    def rebuild_cache(self, server=None):
        servers = [server] if server else self.bot.servers
        for server in servers:
            if server in self._cache:
                del self._cache[server]
            for role in server.roles:
                self._sync_role(role)

    def get_roles(self, server, key):
        return self._cache[server].get(key, set())

    def get_role(self, server, key, *, default=None):
        for role in self.get_roles(server, key):
            return role
        return default

    def roles_by_key(self, server):
        for key, group in self._cache[server].items():
            for role in group:
                yield key, role

    def all_roles(self, server):
        for group in self._cache[server].values():
            yield from group

    def all_keys(self, server):
        return self._cache[server].keys()

    def _sync_role(self, role):
        key = self.key_for_role(role)
        if key:
            self._cache[role.server][key].add(role)

    def _remove_role(self, role):
        key = self.key_for_role(role)
        if key:
            self._cache[role.server][key].remove(role)

    async def on_ready(self):
        self.rebuild_cache()

    async def on_server_role_create(self, role):
        self._sync_role(role)

    async def on_server_role_delete(self, role):
        self._remove_role(role)

    async def on_server_role_update(self, old, new):
        self._remove_role(old)
        self._sync_role(new)

    async def on_server_join(self, server):
        for role in server.roles:
            self._sync_role(role)

    async def on_server_remove(self, server):
        if self._cache[server]:
            del self._cache[server]
