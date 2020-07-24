import asyncio
import sys
import traceback

import discord
from discord.ext import commands

import utils


class AdminTools(commands.Cog, name='Admin'):
    def __init__(self, bot):
        self.bot = bot
        self.deleting = set()

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_id(self, ctx, *, id: str):
        """Bans a user by their Discord ID.

        This can be used to preemptively ban a user who hasn't tried
        to join this guild yet.
        """
        snowflake = discord.Object(id=id)
        await ctx.guild.ban(snowflake, delete_message_days=0)
        await ctx.reply("Banned DiscordID {}.".format(id))

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx):
        """List the Discrd IDs of all banned users.
        """
        banned = await ctx.guild.bans()
        msg = '\n'.join('{} - {}'.format(entry.user.id, str(entry.user))
                        for entry in banned)
        await ctx.reply("banned users: ```{}```".format(msg))

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def delete(self, ctx, *, num_messages: int = 50):
        """Delete recent messages from this channel.

        Pinned messages will be skipped. Requires the the 'Manage
        Messages' permission.
        """
        await self.purge_channel(ctx, num_messages)

    @delete.command(name='all')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def delete_all(self, ctx):
        """Delete all messages from this channel.

        Pinned messages will be skipped. Requires the the 'Manage
        Messages' permission.
        """
        await self.purge_channel(ctx, None)

    @delete.command(name='stop')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def delete_stop(self, ctx):
        """Stop an in-progress message deletion in this channel.
        """
        channel = ctx.message.channel
        if channel in self.deleting:
            self.deleting.remove(channel)
            await ctx.reply("Stopped message deletion process.")
        else:
            await ctx.reply("No message deletion in progress in this channel.")

    @ban_id.error
    @delete.error
    @delete_all.error
    @delete_stop.error
    async def missing_permissions(self, error, ctx):
        if utils.is_local_check_failure(error):
            message = ("Permissions check failed. Either you're not allowed to use that "
                       "command or the bot is missing a permission required to execute it.")
            await ctx.reply(message)

    async def purge_channel(self, ctx, num_messages=None):
        channel = ctx.channel
        if channel.id in self.deleting:
            await ctx.reply("Deletion already in progress, be patient.")
            return

        try:
            self.deleting.add(channel.id)
            deletion_notice = await ctx.send("Starting mass deletion...")
            pinned_ids = set(m.id for m in await ctx.pins())

            def check(m):
                return m.id != deletion_notice.id and m.id not in pinned_ids

            deleted_so_far = 0
            while channel.id in self.deleting:
                msg = "Deletion in progress ({}/{})..."
                await deletion_notice.edit(content=msg.format(deleted_so_far, num_messages or '\u221E'))

                limit = 100 if num_messages is None else num_messages - deleted_so_far
                deleted = await channel.purge(limit=limit, check=check, before=deletion_notice)
                deleted_so_far += len(deleted)

                if not deleted:
                    break

            await deletion_notice.edit(content="Deleted {} messages.".format(deleted_so_far))
        finally:
            if channel.id in self.deleting:
                self.deleting.remove(channel.id)
