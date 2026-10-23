import asyncio

import discord
from discord.ext import commands

from bot.config import get_guild_id, get_token, logger

# Member-join onboarding requires the privileged Server Members Intent to be enabled
# in both code and the Discord Developer Portal.
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def load_cogs() -> None:
    """Load all cogs from the bot.cogs package."""
    await bot.load_extension("bot.cogs.ping")
    logger.info("Loaded cog: bot.cogs.ping")
    await bot.load_extension("bot.cogs.initiate")
    logger.info("Loaded cog: bot.cogs.initiate")


async def sync_commands() -> None:
    """Sync slash commands to the test guild (fast) or globally (slow)."""
    guild_id = get_guild_id()
    if guild_id is not None:
        guild = discord.Object(id=guild_id)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logger.info("Synced %d command(s) to guild %s", len(synced), guild_id)
    else:
        synced = await bot.tree.sync()
        logger.info("Synced %d command(s) globally (may take up to an hour to appear)", len(synced))


@bot.event
async def on_ready() -> None:
    """Log a successful connection and sync commands once."""
    logger.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
    if get_guild_id() is not None:
        await sync_commands()


async def main() -> None:
    """Load cogs, sync commands, and start the bot."""
    await load_cogs()
    try:
        token = get_token()
        await bot.start(token)
    except RuntimeError as e:
        logger.error("Startup failed: %s", e)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
