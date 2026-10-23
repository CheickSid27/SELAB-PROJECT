import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest

from app.db import connect


@pytest.fixture
def conn():
    return connect(":memory:")
