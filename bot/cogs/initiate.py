import re

import discord
from discord import app_commands
from discord.ext import commands

CHANNEL_TOPIC_PREFIX = "meerkat-owner:"


def channel_slug(member: discord.Member) -> str:
    """Create a stable, Discord-safe channel suffix for a member."""
    name = re.sub(r"[^a-z0-9-]+", "-", member.display_name.lower()).strip("-")
    return (name or "member")[:80].strip("-") or "member"


def owned_channel_topic(member_id: int, channel_kind: str) -> str:
    """Return the topic marker used to recognize channels managed for a member."""
    return f"meerkat-owner:{member_id}:{channel_kind}"


class Initiate(commands.Cog):
    """New-member onboarding and personal channel setup."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Send new members a short onboarding DM."""
        start_here = discord.utils.get(member.guild.text_channels, name="start-here")
        channel_reference = start_here.mention if start_here else "#start-here"
        message = (
            f"Welcome to **{member.guild.name}**! Please visit {channel_reference} to get started.\n\n"
            "You can use `/initiate` to set up your personal TDL and monthlies channels. "
            "More bot instructions will be added here soon."
        )
        try:
            await member.send(message)
        except (discord.Forbidden, discord.HTTPException):
            # Members may have DMs disabled; joining should not break the bot.
            return

    @app_commands.command(
        name="initiate",
        description="Set up personal TDL and monthlies channels.",
    )
    @app_commands.describe(user="Member to set up (defaults to you).")
    async def initiate(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        """Create private TDL and monthlies channels for a member."""
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        target = user or interaction.user
        if not isinstance(target, discord.Member):
            await interaction.response.send_message(
                "I couldn't resolve that member in this server.",
                ephemeral=True,
            )
            return

        if target.guild.id != interaction.guild.id:
            await interaction.response.send_message(
                "The selected member must belong to this server.",
                ephemeral=True,
            )
            return

        tdl_topic = owned_channel_topic(target.id, "tdl")
        monthlies_topic = owned_channel_topic(target.id, "monthlies")
        existing_topics = {
            channel.topic
            for channel in interaction.guild.text_channels
            if channel.topic is not None
        }
        if tdl_topic in existing_topics or monthlies_topic in existing_topics:
            await interaction.response.send_message(
                f"{target.mention} already has initiation channels. No channels were created.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            target: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
        }
        if interaction.guild.me is not None:
            overwrites[interaction.guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )

        slug = channel_slug(target)
        created: list[discord.TextChannel] = []
        try:
            tdl = await interaction.guild.create_text_channel(
                f"tdl-{slug}",
                topic=tdl_topic,
                overwrites=overwrites,
                reason=f"Meerkat initiation for member {target.id}",
            )
            created.append(tdl)
            monthlies = await interaction.guild.create_text_channel(
                f"monthlies-{slug}",
                topic=monthlies_topic,
                overwrites=overwrites,
                reason=f"Meerkat initiation for member {target.id}",
            )
            created.append(monthlies)
        except discord.HTTPException:
            for channel in created:
                try:
                    await channel.delete(reason="Rollback incomplete Meerkat initiation")
                except discord.HTTPException:
                    pass
            await interaction.followup.send(
                "I couldn't create the channels. Please check that I have Manage Channels permission and try again.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Created private channels for {target.mention}: {tdl.mention} and {monthlies.mention}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    """Entry point for the cog loader."""
    await bot.add_cog(Initiate(bot))
