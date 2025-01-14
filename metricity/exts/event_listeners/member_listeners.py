"""An ext to listen for member events and syncs them to the database."""

import discord
from asyncpg.exceptions import UniqueViolationError
from discord.ext import commands

from metricity.bot import Bot
from metricity.config import BotConfig
from metricity.models import User


class MemberListeners(commands.Cog):
    """Listen for member events and sync them to the database."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """On a user leaving the server mark in_guild as False."""
        await self.bot.sync_process_complete.wait()

        if member.guild.id != BotConfig.guild_id:
            return

        if db_user := await User.get(str(member.id)):
            await db_user.update(
                in_guild=False
            ).apply()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """On a user joining the server add them to the database."""
        await self.bot.sync_process_complete.wait()

        if member.guild.id != BotConfig.guild_id:
            return

        if db_user := await User.get(str(member.id)):
            await db_user.update(
                id=str(member.id),
                name=member.name,
                avatar_hash=getattr(member.avatar, "key", None),
                guild_avatar_hash=getattr(member.guild_avatar, "key", None),
                joined_at=member.joined_at,
                created_at=member.created_at,
                is_staff=BotConfig.staff_role_id in [role.id for role in member.roles],
                public_flags=dict(member.public_flags),
                pending=member.pending,
                in_guild=True
            ).apply()
        else:
            try:
                await User.create(
                    id=str(member.id),
                    name=member.name,
                    avatar_hash=getattr(member.avatar, "key", None),
                    guild_avatar_hash=getattr(member.guild_avatar, "key", None),
                    joined_at=member.joined_at,
                    created_at=member.created_at,
                    is_staff=BotConfig.staff_role_id in [role.id for role in member.roles],
                    public_flags=dict(member.public_flags),
                    pending=member.pending,
                    in_guild=True
                )
            except UniqueViolationError:
                pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, member: discord.Member) -> None:
        """When a member updates their profile, update the DB record."""
        await self.bot.sync_process_complete.wait()

        if member.guild.id != BotConfig.guild_id:
            return

        # Joined at will be null if we are not ready to process events yet
        if not member.joined_at:
            return

        roles = set([role.id for role in member.roles])

        if db_user := await User.get(str(member.id)):
            if (
                db_user.name != member.name or
                db_user.avatar_hash != getattr(member.avatar, "key", None) or
                db_user.guild_avatar_hash != getattr(member.guild_avatar, "key", None) or
                BotConfig.staff_role_id in
                [role.id for role in member.roles] != db_user.is_staff
                or db_user.pending is not member.pending
            ):
                await db_user.update(
                    id=str(member.id),
                    name=member.name,
                    avatar_hash=getattr(member.avatar, "key", None),
                    guild_avatar_hash=getattr(member.guild_avatar, "key", None),
                    joined_at=member.joined_at,
                    created_at=member.created_at,
                    is_staff=BotConfig.staff_role_id in roles,
                    public_flags=dict(member.public_flags),
                    in_guild=True,
                    pending=member.pending
                ).apply()
        else:
            try:
                await User.create(
                    id=str(member.id),
                    name=member.name,
                    avatar_hash=getattr(member.avatar, "key", None),
                    guild_avatar_hash=getattr(member.guild_avatar, "key", None),
                    joined_at=member.joined_at,
                    created_at=member.created_at,
                    is_staff=BotConfig.staff_role_id in roles,
                    public_flags=dict(member.public_flags),
                    in_guild=True,
                    pending=member.pending
                )
            except UniqueViolationError:
                pass


async def setup(bot: Bot) -> None:
    """Load the MemberListeners cog."""
    await bot.add_cog(MemberListeners(bot))
