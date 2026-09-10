from app.domain.auth.role_rules import resolve_role_by_email

ADMIN_EMAILS = "admin@governai.com, second-admin@governai.com"


def resolve(email):
    return resolve_role_by_email(email, admin_emails=ADMIN_EMAILS)


def test_listed_admin_email_gets_admin():
    assert resolve("admin@governai.com") == "admin"


def test_second_listed_admin_email_also_gets_admin():
    assert resolve("second-admin@governai.com") == "admin"


def test_unlisted_email_gets_agent_builder():
    assert resolve("nobody@example.com") == "agent_builder"


def test_no_email_gets_agent_builder():
    assert resolve(None) == "agent_builder"


def test_matching_is_case_insensitive():
    assert resolve("ADMIN@GovernAI.com") == "admin"


def test_matching_ignores_incidental_whitespace_in_the_configured_list():
    assert (
        resolve_role_by_email(
            "admin@governai.com",
            admin_emails=" admin@governai.com ",
        )
        == "admin"
    )


def test_an_email_cannot_be_both_never_promoted_by_a_partial_match():
    # "admin@governai.com.evil.com" must not match "admin@governai.com".
    assert resolve("admin@governai.com.evil.com") == "agent_builder"
