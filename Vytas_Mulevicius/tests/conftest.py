import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def mock_st_calls(monkeypatch):
    """
    Patch Streamlit UI calls globally so tests don't require a running
    Streamlit server. st.stop() in particular would raise StopException
    and abort test execution without this.
    """
    import streamlit as st

    monkeypatch.setattr(st, 'info', MagicMock())
    monkeypatch.setattr(st, 'success', MagicMock())
    monkeypatch.setattr(st, 'error', MagicMock())
    monkeypatch.setattr(st, 'stop', MagicMock())

    spinner_ctx = MagicMock()
    spinner_ctx.__enter__ = MagicMock(return_value=None)
    spinner_ctx.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(st, 'spinner', MagicMock(return_value=spinner_ctx))
