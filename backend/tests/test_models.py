from app.models import User


def test_user_set_verify_password(db_session):
    user = User(
        full_name="Model Test",
        email="model@test.com",
        mobile="1112223333",
    )
    user.set_password("mysecretpw")
    db_session.add(user)
    db_session.commit()

    fetched = db_session.query(User).filter(User.email == "model@test.com").one()
    assert fetched.verify_password("mysecretpw")
    assert not fetched.verify_password("wrongpw")


def test_user_create(db_session):
    user = User(
        full_name="Creator",
        email="creator@test.com",
        mobile="4445556666",
    )
    user.set_password("abc12345")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.full_name == "Creator"
    assert user.email == "creator@test.com"
    assert user.mobile == "4445556666"
    assert user.created_at is not None
    assert user.hashed_password != "abc12345"
