from app.auth.security import hash_password, verify_password


def test_correct_password_verifies():
    hashed = hash_password("demo1234")
    assert hashed != "demo1234"
    assert verify_password("demo1234", hashed)


def test_wrong_password_fails():
    hashed = hash_password("demo1234")
    assert not verify_password("wrong-password", hashed)
