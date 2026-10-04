import pytest
from project_test_project import greet


def test_greeting_trims_name():
    assert greet(" Ada ") == "Hello, Ada!"


def test_greeting_requires_name():
    with pytest.raises(ValueError):
        greet(" ")
