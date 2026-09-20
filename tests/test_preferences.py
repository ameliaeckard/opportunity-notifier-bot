from bot.views.preferences import opportunity_prompt_embed


def test_public_opportunity_prompt_matches_private_setup_copy():
    embed = opportunity_prompt_embed()
    assert embed.title == "Opportunity Notifications"
    assert embed.description == "Would you like private DMs when new internships or hackathons are found?"
    assert embed.footer.text == "You must explicitly opt in before any notification is sent."
