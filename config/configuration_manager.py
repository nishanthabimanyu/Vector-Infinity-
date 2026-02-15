"""
Configuration Manager for Astronomical Dating System

Handles saving/loading constraint sets to/from JSON files.
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple
import logging
import re

from config.constraint_serializer import ConstraintSerializer

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages persistent storage of constraint sets.
    
    Saves constraint configurations as JSON files in the user's home directory.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Optional custom config directory. 
                       Defaults to ~/.vector_infinity/saved_queries/
        """
        if config_dir is None:
            home = Path.home()
            config_dir = home / '.vector_infinity' / 'saved_queries'
        
        self.config_dir = Path(config_dir)
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Config directory: {self.config_dir}")
        except Exception as e:
            logger.error(f"Failed to create config directory: {e}")
            raise
    
    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Sanitize a config name for use as filename.
        
        Replaces spaces and special chars with underscores.
        """
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized.lower()
    
    def save_constraint_set(self, name: str, constraints: List,
                           description: str = "", search_params: dict = None) -> Path:
        """
        Save a constraint set to JSON file.
        
        Args:
            name: Name for this constraint set
            constraints: List of BayesianConstraint instances
            description: Optional description
            search_params: Optional search parameters dict
            
        Returns:
            Path to saved JSON file
        """
        # Serialize to dict
        data = ConstraintSerializer.serialize_constraint_set(
            constraints=constraints,
            name=name,
            description=description,
            search_params=search_params
        )
        
        # Generate filename
        filename = self._sanitize_name(name) + '.json'
        filepath = self.config_dir / filename
        
        # Write to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved constraint set: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Failed to save constraint set: {e}")
            raise
    
    def load_constraint_set(self, name: str) -> Tuple[List, str, str, dict]:
        """
        Load a constraint set from JSON file.
        
        Args:
            name: Name of constraint set (with or without .json extension)
            
        Returns:
            Tuple of (constraints_list, name, description, search_params)
            
        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        # Handle both "name" and "name.json"
        if not name.endswith('.json'):
            filename = self._sanitize_name(name) + '.json'
        else:
            filename = name
        
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        # Read from file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Deserialize
            constraints, name, desc, params = ConstraintSerializer.deserialize_constraint_set(data)
            
            logger.info(f"Loaded constraint set '{name}' with {len(constraints)} constraints")
            return constraints, name, desc, params
        
        except Exception as e:
            logger.error(f"Failed to load constraint set: {e}")
            raise
    
    def list_saved_sets(self) -> List[dict]:
        """
        List all saved constraint sets.
        
        Returns:
            List of dicts with 'name', 'filename', 'path' keys
        """
        configs = []
        
        try:
            for filepath in self.config_dir.glob('*.json'):
                # Try to load metadata
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    configs.append({
                        'name': data.get('name', filepath.stem),
                        'filename': filepath.name,
                        'path': str(filepath),
                        'description': data.get('description', ''),
                        'num_constraints': len(data.get('constraints', []))
                    })
                except Exception as e:
                    logger.warning(f"Could not read {filepath.name}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to list configs: {e}")
        
        return sorted(configs, key=lambda x: x['name'])
    
    def delete_constraint_set(self, name: str) -> bool:
        """
        Delete a saved constraint set.
        
        Args:
            name: Name of constraint set to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        filename = self._sanitize_name(name) + '.json'
        filepath = self.config_dir / filename
        
        try:
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted constraint set: {filepath}")
                return True
            else:
                logger.warning(f"Config file not found: {filepath}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete constraint set: {e}")
            return False


if __name__ == '__main__':
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    print("Configuration Manager Demo")
    print("="*60)
    
    manager = ConfigurationManager()
    print(f"\nConfig directory: {manager.config_dir}")
    
    # List existing configs
    configs = manager.list_saved_sets()
    print(f"\nFound {len(configs)} saved configurations:")
    for cfg in configs:
        print(f"  - {cfg['name']} ({cfg['num_constraints']} constraints)")
