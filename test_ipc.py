from tray_app import parse_authenticated_ipc


def test_authenticated_ipc_accepts_matching_token():
    assert parse_authenticated_ipc("correct-token TOGGLE", "correct-token") == "TOGGLE"


def test_authenticated_ipc_rejects_missing_or_wrong_token():
    assert parse_authenticated_ipc("TOGGLE", "correct-token") is None
    assert parse_authenticated_ipc("wrong-token TOGGLE", "correct-token") is None
