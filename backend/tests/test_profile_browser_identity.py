from types import SimpleNamespace
import pytest
from app.api import group2
from app.api.errors import DomainError


def test_public_profile_remains_anonymous_without_credentials(monkeypatch):
    def refuse(*args): raise AssertionError('Anonymous reads should not authenticate')
    monkeypatch.setattr(group2,'identity',refuse)
    assert group2.optional_identity(SimpleNamespace(cookies={}),None,object()) is None


@pytest.mark.parametrize('cookie,credentials',[('browser-session',None),(None,object())])
def test_profile_reuses_authenticated_identity_for_cookie_and_bearer(monkeypatch,cookie,credentials):
    request=SimpleNamespace(cookies={'aroundyou_session':cookie} if cookie else {})
    db=object();user=object();calls=[]
    def identify(r,c,d):calls.append((r,c,d));return user
    monkeypatch.setattr(group2,'identity',identify)
    assert group2.optional_identity(request,credentials,db) is user
    assert calls==[(request,credentials,db)]


def test_invalid_browser_session_is_not_silently_treated_as_anonymous(monkeypatch):
    def identify(*args):raise DomainError('unauthenticated','Sign in to continue',401)
    monkeypatch.setattr(group2,'identity',identify)
    with pytest.raises(DomainError):
        group2.optional_identity(SimpleNamespace(cookies={'aroundyou_session':'expired'}),None,object())
