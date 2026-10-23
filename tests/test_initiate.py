import discord
from discord import app_commands

from bot.cogs.initiate import Initiate, channel_slug, owned_channel_topic


def test_initiate_slash_command_exists() -> None:
    command = Initiate.initiate
    assert isinstance(command, app_commands.Command)
    assert command.name == "initiate"
    assert len(command.parameters) == 1
    assert command.parameters[0].name == "user"
    assert command.parameters[0].required is False


def test_channel_slug_is_discord_safe() -> None:
    member = type("MemberStub", (), {"display_name": "Aaqib Khan / Test"})()
    assert channel_slug(member) == "aaqib-khan-test"


def test_owned_channel_topic_is_unique_per_member_and_kind() -> None:
    assert owned_channel_topic(123, "tdl") == "meerkat-owner:123:tdl"
    assert owned_channel_topic(123, "monthlies") != owned_channel_topic(123, "tdl")
    assert owned_channel_topic(456, "tdl") != owned_channel_topic(123, "tdl")
