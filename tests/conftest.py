import os
import pytest

from dotenv import load_dotenv

load_dotenv(override=True)


@pytest.fixture
def api_key():
    yield os.environ.get("TEST_API_KEY", "fake_key")
