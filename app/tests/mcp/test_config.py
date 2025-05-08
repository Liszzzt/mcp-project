import os
import json

import pytest

from app.mcp.config import Config

@pytest.fixture
def temp_config(tmp_path):
    config_file = tmp_path / "test_config.json"
    config_file.write_text("""
        {
            "mcpServers": {
                "test-server": {
                    "command": "test",
                    "args": ["${TEST_VAR}", "${OTHER_VAR}"]
                }
            }
        }
    """)
    return config_file

@pytest.fixture
def temp_env(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("""
                        TEST_VAR=test_value
                        OTHER_VAR=other_value
                        """)
    return env_file

def test_load_config_with_env(temp_config, temp_env):
    config = Config(temp_config, temp_env)
    server_config = config.get_server_config("test-server")
    assert server_config["command"] == "test"
    assert server_config["args"] == ["test_value", "other_value"]

def test_load_config_without_env(temp_config):
    config = Config(temp_config)
    server_config = config.get_server_config("test-server")
    assert server_config["command"] == "test"
    # Variables should remain unchanged when no env file is provided
    assert server_config["args"] == ["${TEST_VAR}", "${OTHER_VAR}"]

def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        Config("nonexistent.json")

def test_invalid_json_config(tmp_path):
    invalid_config = tmp_path / "invalid.json"
    invalid_config.write_text("{invalid json}")
    
    with pytest.raises(json.JSONDecodeError):
        Config(invalid_config)

def test_missing_server_config(temp_config):
    config = Config(temp_config)
    with pytest.raises(KeyError):
        config.get_server_config("nonexistent-server")

def test_env_variable_not_found(temp_config, temp_env):
    config = Config(temp_config, temp_env)
    os.environ.pop("OTHER_VAR", None)  # Ensure variable is not in environment
    server_config = config.get_server_config("test-server")
    assert server_config["args"][1] == "${OTHER_VAR}"  # Should keep original when var not found
