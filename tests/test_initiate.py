from bot.cogs.initiate import channel_slug, owned_channel_topic


def test_channel_slug_is_discord_safe() -> None:
    member = type("MemberStub", (), {"display_name": "Aaqib Khan / Test"})()
    assert channel_slug(member) == "aaqib-khan-test"


def test_owned_channel_topic_is_unique_per_member_and_kind() -> None:
    assert owned_channel_topic(123, "tdl") == "meerkat-owner:123:tdl"
    assert owned_channel_topic(123, "monthlies") != owned_channel_topic(123, "tdl")
    assert owned_channel_topic(456, "tdl") != owned_channel_topic(123, "tdl")
