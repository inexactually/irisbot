import asyncio
import sys
import traceback

import discord
from discord.ext import commands

import utils

class AdminTools:
    def __init__(self, bot):
        self.bot = bot
        self.deleting = set()

    @commands.command(no_pm=True, pass_context=True)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_id(self, ctx, *, id : str):
        """Bans a user by their Discord ID.

        This can be used to preemptively ban a user who hasn't tried
        to join this server yet.
        """
        server = ctx.message.server
        member = discord.Member(user=dict(id=id), server=server)
        await self.bot.ban(member, delete_message_days=0)
        await self.bot.reply("Banned DiscordID {}.".format(id))

    @commands.command(no_pm=True, pass_context=True)
    @commands.has_permissions(administrator=True)
    async def list_bans(self, ctx):
        banned = await self.bot.get_bans(ctx.message.server)
        msg = '\n'.join('{} - {}'.format(user.id, str(user)) for user in banned)
        await self.bot.reply("banned users: ```{}```".format(msg))

    @commands.group(no_pm=True, pass_context=True, invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def delete(self, ctx, *, num_messages : int = 50):
        """Delete recent messages from this channel.

        Pinned messages will be skipped. Requires the the 'Manage
        Messages' permission.
        """
        await self.purge_channel(ctx.message.channel, num_messages)

    @delete.command(no_pm=True, pass_context=True, name='all')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def delete_all(self, ctx):
        """Delete all messages from this channel.

        Pinned messages will be skipped. Requires the the 'Manage
        Messages' permission.
        """
        await self.purge_channel(ctx.message.channel, None)

    @delete.command(no_pm=True, pass_context=True, name='stop')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def delete_stop(self, ctx):
        """Stop an in-progress message deletion in this channel.
        """
        channel = ctx.message.channel
        if channel in self.deleting:
            self.deleting.remove(channel)
            await self.bot.reply("Stopped message deletion process.")
        else:
            await self.bot.reply("No message deletion in progress in this channel.")

    @ban_id.error
    @delete.error
    @delete_all.error
    @delete_stop.error
    async def missing_permissions(self, error, ctx):
        if utils.is_local_check_failure(error):
            message = ("Permissions check failed. Either you're not allowed to use that "
                       "command or the bot is missing a permission required to execute it.")
            await self.bot.reply(message)

    async def purge_channel(self, channel, num_messages=None):
        if channel in self.deleting:
            await self.bot.reply("Deletion already in progress, be patient.")
            return

        try:
            self.deleting.add(channel)
            deletion_notice = await self.bot.say("Starting mass deletion...")
            pinned_ids = set(m.id for m in await self.bot.pins_from(channel))

            def check(m):
                return m.id != deletion_notice.id and m.id not in pinned_ids

            deleted_so_far = 0
            while channel in self.deleting:
                msg = "Deletion in progress ({}/{})..."
                await self.bot.edit_message(deletion_notice, msg.format(deleted_so_far, num_messages or '\u221E'))

                limit = 100 if num_messages is None else num_messages - deleted_so_far
                deleted = await self.thorough_purge_from(channel, limit=limit, check=check, before=deletion_notice)
                deleted_so_far += len(deleted)

                if not deleted:
                    break

            await self.bot.edit_message(deletion_notice, "Deleted {} messages.".format(deleted_so_far))
        finally:
            if channel in self.deleting:
                self.deleting.remove(channel)

    async def thorough_purge_from(self, channel, check=None, limit=100, **kwargs):
        """Discord's bulk delete doesn't work on messages older than 2
        weeks, so instead we have to do... this.
        """
        try:
            deleted = await self.bot.purge_from(channel, check=check, limit=limit, **kwargs)
            if deleted:
                return deleted
        except discord.errors.HTTPException as exception:
            pass

        # fall back to the sloooooow version
        deleted = []
        iterator = self.bot.logs_from(channel, limit, **kwargs)
        while True:
            try:
                message = await iterator.iterate()
                if not check or check(message):
                    await self.bot.delete_message(message)
                    deleted.append(message)
            except asyncio.QueueEmpty:
                return deleted
