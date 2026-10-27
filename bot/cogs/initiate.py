import re

import discord
from discord import app_commands
from discord.ext import commands

# Temporary ownership markers stored in channel topics. This is intentionally
# replaceable if Meerkat moves channel ownership tracking into a database.
CHANNEL_TOPIC_PREFIX = "meerkat-owner:"


def channel_slug(name: str | discord.Member) -> str:
    """Create a stable, Discord-safe channel slug from a name or member."""
    display_name = name if isinstance(name, str) else name.display_name
    slug = re.sub(r"[^a-z0-9-]+", "-", display_name.lower()).strip("-")
    return (slug or "member")[:80].strip("-") or "member"


def owned_channel_topic(member_id: int, channel_kind: str) -> str:
    """Return the temporary topic marker used to recognize managed channels."""
    return f"{CHANNEL_TOPIC_PREFIX}{member_id}:{channel_kind}"


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
    @app_commands.describe(
        user="Member to set up (defaults to you).",
        channel_name="Optional name for your channels (defaults to the member's display name).",
    )
    async def initiate(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
        channel_name: str | None = None,
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

        slug = channel_slug(channel_name or target.display_name)
        # TDL and monthlies channels share the member's slug; their categories
        # distinguish the channel types. If a category is not configured yet,
        # Discord creates the channel at the server root.
        tdl_category = next(
            (category for category in interaction.guild.categories
             if category.name.casefold() in {"tdl", "tdls"}),
            None,
        )
        monthlies_category = next(
            (category for category in interaction.guild.categories
             if category.name.casefold() in {"monthlies", "monthly"}),
            None,
        )

        created: list[discord.TextChannel] = []
        try:
            tdl = await interaction.guild.create_text_channel(
                slug,
                category=tdl_category,
                topic=tdl_topic,
                overwrites=overwrites,
                reason=f"Meerkat initiation for member {target.id}",
            )
            created.append(tdl)
            monthlies = await interaction.guild.create_text_channel(
                slug,
                category=monthlies_category,
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
