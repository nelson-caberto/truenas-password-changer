"""Pytest configuration and fixtures."""

import os
import pytest
from unittest.mock import patch

# Configure tests to use WebSocket client for backward compatibility
os.environ['TRUENAS_CLIENT'] = 'websocket'


@pytest.fixture(autouse=True)
def setup_env():
    """Ensure WebSocket client is used for all tests."""
    os.environ['TRUENAS_CLIENT'] = 'websocket'
    yield
    os.environ['TRUENAS_CLIENT'] = 'websocket'
