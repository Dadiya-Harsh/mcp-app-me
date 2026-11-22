import pytest

from tests.helpers import Caller, make_server


@pytest.fixture
def client() -> Caller:
    """A client on a server that reads the test fixtures."""
    return Caller(make_server())
