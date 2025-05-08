import json
import os
import re
from typing import Any
from pathlib import Path
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Handles loading and processing of server configurations."""

    def __init__(self, config_path: str | Path, env_path: str | Path | None = None) -> None:
        """
        Initialize Config with paths to configuration files.
        
        Args:
            config_path: Path to the servers_config.json file
            env_path: Optional path to .env file
        """
        self.config_path = Path(config_path)
        self.env_path = Path(env_path) if env_path else None
        self.raw_config: dict[str, Any] = {}
        
        self._load_config()

    def _load_config(self) -> None:
        """Load and process configuration from files."""
        # Load environment variables
        self.use_env = False
        if self.env_path and self.env_path.exists():
            logger.info(f"Loading environment variables from {self.env_path}")
            load_dotenv(self.env_path)
            self.use_env = True
        
        # Load JSON config
        try:
            with open(self.config_path, 'r') as f:
                self.raw_config = json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise

        logger.info(f"Configuration loaded successfully, {len(self.raw_config)} servers found.")

    def _substitute_variables(self, config: Any) -> Any:
        """
        Recursively substitute variables in configuration.
        
        Args:
            config: Configuration object (dict, list, or primitive)
            
        Returns:
            Configuration with variables substituted
        """
        if isinstance(config, dict):
            return {k: self._substitute_variables(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_variables(item) for item in config]
        elif isinstance(config, str):
            return self._replace_variables(config)
        return config

    def _replace_variables(self, value: str) -> str:
        """
        Replace ${VAR} patterns with environment variable values.
        
        Args:
            value: String containing variable references
            
        Returns:
            String with variables replaced by their values
        """
        if not self.use_env:
            return value

        def replace(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            if env_value is None:
                logger.warning(f"Environment variable not found: {var_name}")
                return match.group(0)  # Keep original if not found
            return env_value

        pattern = r'\${([^}]+)}'
        return re.sub(pattern, replace, value)

    def get_server_config(self, server_name: str) -> dict[str, Any]:
        """
        Get configuration for a specific server with processed environment variables.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server configuration dictionary with processed variables
            
        Raises:
            KeyError: If server configuration is not found
        """
        try:
            server_config = self.raw_config["mcpServers"][server_name]
            return self._substitute_variables(server_config)
        except KeyError:
            logger.error(f"Server configuration not found: {server_name}")
            raise
