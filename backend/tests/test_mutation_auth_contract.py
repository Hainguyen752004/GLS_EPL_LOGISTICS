from types import SimpleNamespace

import pytest


def test_scheduling_actor_rejects_missing_principal():
    from routes.tms_planning_routes import _actor

    with pytest.raises(Exception) as error:
        _actor(SimpleNamespace(state=SimpleNamespace(principal=None)))

    assert error.value.code == "AUTHENTICATION_REQUIRED"


def test_scheduling_actor_accepts_authenticated_principal():
    from routes.tms_planning_routes import _actor

    assert _actor(SimpleNamespace(state=SimpleNamespace(principal="dispatcher"))) == "dispatcher"
