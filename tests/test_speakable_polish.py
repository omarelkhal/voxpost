from voxpost.speakable_polish import polish_for_tts


def test_polish_french_day_jeu():
    assert (
        polish_for_tts("Réunion JEU à 14h", lang="fr")
        == "Réunion jeudi à quatorze heures"
    )


def test_polish_french_day_all_caps_only():
    # Lowercase "jeu" (game) is left alone.
    assert polish_for_tts("un jeu sympa", lang="fr") == "un jeu sympa"
    assert polish_for_tts("un JEU sympa", lang="fr") == "un jeudi sympa"


def test_polish_english_shorthand():
    line = polish_for_tts("Team mtg tmrw at 2pm pls", lang="en")
    assert "meeting" in line
    assert "tomorrow" in line
    assert "please" in line


def test_polish_english_day():
    assert polish_for_tts("Call on Wed afternoon", lang="en") == "Call on Wednesday afternoon"


def test_polish_symbols():
    assert "and" in polish_for_tts("Q1 & Q2", lang="en")
    assert "50 percent" in polish_for_tts("50% done", lang="all")
    assert "fifty percent" in polish_for_tts("50% done", lang="en")


def test_polish_strips_at_sign_addresses():
    assert "@" not in polish_for_tts("Email partners@affiliaxe.com", lang="en")


def test_polish_24h_time_en():
    line = (
        "OMAR EL wants to book a pitch workshop at the Garage Comedy Club "
        "in Marseille on May 18th at 18h-"
    )
    out = polish_for_tts(line, lang="en")
    assert "18h" not in out
    assert "six p.m." in out


def test_polish_24h_with_minutes_en():
    out = polish_for_tts("Meeting at 14h30 tomorrow", lang="en")
    assert "14h30" not in out
    assert "two thirty p.m." in out


def test_polish_clock_12h_en():
    out = polish_for_tts("Team mtg tmrw at 2pm pls", lang="en")
    assert "2pm" not in out.lower()
    assert "two p.m." in out


def test_polish_24h_colon_en():
    assert "six thirty p.m." in polish_for_tts("Call at 18:30", lang="en")
