"""
Constraint Serialization for JSON Export/Import

Provides registry-based serialization for all BayesianConstraint subclasses.
"""

from typing import Dict, List, Type
import logging

logger = logging.getLogger(__name__)


class ConstraintSerializer:
    """
    Serializes and deserializes constraint objects to/from JSON-compatible dictionaries.
    
    Uses a type registry to map constraint class names to their implementations.
    """
    
    # Registry mapping classConstraint type names to classes
    _registry: Dict[str, Type] = {}
    
    @classmethod
    def register_constraint(cls, constraint_class: Type):
        """
        Register a constraint class for serialization.
        
        Args:
            constraint_class: BayesianConstraint subclass
        """
        class_name = constraint_class.__name__
        cls._registry[class_name] = constraint_class
        logger.debug(f"Registered constraint: {class_name}")
    
    @classmethod
    def serialize_constraint(cls, constraint) -> dict:
        """
        Serialize a single constraint to dictionary.
        
        Args:
            constraint: BayesianConstraint instance
            
        Returns:
            Dict with constraint data
        """
        return constraint.to_dict()
    
    @classmethod
    def deserialize_constraint(cls, data: dict):
        """
        Deserialize a single constraint from dictionary.
        
        Args:
            data: Dict with 'type' and 'params' keys
            
        Returns:
            BayesianConstraint instance
            
        Raises:
            ValueError: If constraint type not registered
        """
        constraint_type = data.get('type')
        
        if constraint_type not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(
                f"Unknown constraint type: '{constraint_type}'. "
                f"Available types: {available}"
            )
        
        constraint_class = cls._registry[constraint_type]
        return constraint_class.from_dict(data)
    
    @classmethod
    def serialize_constraint_set(cls, constraints: List, name: str, description: str = "",
                                 search_params: dict = None) -> dict:
        """
        Serialize a complete constraint set to dictionary.
        
        Args:
            constraints: List of BayesianConstraint instances
            name: Name for this constraint set
            description: Optional description
            search_params: Optional search parameters (start_jd, end_jd, step_days, threshold)
            
        Returns:
            Dict ready for JSON export
        """
        return {
            'version': '1.0',
            'name': name,
            'description': description,
            'constraints': [cls.serialize_constraint(c) for c in constraints],
            'search_params': search_params or {}
        }
    
    @classmethod
    def deserialize_constraint_set(cls, data: dict) -> tuple:
        """
        Deserialize a complete constraint set from dictionary.
        
        Args:
            data: Dict from JSON with constraint set data
            
        Returns:
            Tuple of (constraints_list, name, description, search_params)
        """
        version = data.get('version', '1.0')
        if version != '1.0':
            logger.warning(f"Unsupported version: {version}. Attempting to load anyway.")
        
        name = data.get('name', 'Unnamed')
        description = data.get('description', '')
        search_params = data.get('search_params', {})
        
        constraints = []
        for constraint_data in data.get('constraints', []):
            try:
                constraint = cls.deserialize_constraint(constraint_data)
                constraints.append(constraint)
            except Exception as e:
                logger.error(f"Failed to deserialize constraint: {e}")
                # Continue loading other constraints
        
        return constraints, name, description, search_params


# Auto-register all known constraint types
def _auto_register():
    """Automatically register all constraint types from constraints module."""
    try:
        from constraints import (
            ConstraintConstellation,
            ConstraintConjunction,
            ConstraintRetrograde
        )
        
        ConstraintSerializer.register_constraint(ConstraintConstellation)
        ConstraintSerializer.register_constraint(ConstraintConjunction)
        ConstraintSerializer.register_constraint(ConstraintRetrograde)
        
        logger.debug("Auto-registered 3 constraint types")
    except ImportError as e:
        logger.warning(f"Could not auto-register constraints: {e}")


# Run auto-registration on module import
_auto_register()
