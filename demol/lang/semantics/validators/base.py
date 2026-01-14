"""
Base Validator Class

This module provides the abstract base class that all validators should inherit from.
This makes it easy to add new validation rules with a consistent interface.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseValidator(ABC):
    """
    Abstract base class for all validators.
    
    To create a new validator:
    1. Inherit from this class
    2. Implement the validate() method with your validation logic
    3. Implement get_name() to return a human-readable name
    4. Implement get_description() to describe what the validator checks
    
    Example:
        class MyValidator(BaseValidator):
            @staticmethod
            def get_name() -> str:
                return "My Validation Rule"
            
            @staticmethod
            def get_description() -> str:
                return "Checks that my specific condition is met"
            
            @staticmethod
            def validate(model, **kwargs):
                # Your validation logic here
                pass
    """
    
    @staticmethod
    @abstractmethod
    def validate(*args, **kwargs) -> None:
        """
        Perform the validation.
        
        This method should use raise_validation_error() or raise_validation_warning()
        from the core module to report issues.
        
        Args:
            *args: Positional arguments (varies by validator)
            **kwargs: Keyword arguments (varies by validator)
        
        Raises:
            NotImplementedError: If not overridden in subclass
        """
        raise NotImplementedError("Subclasses must implement validate()")
    
    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """
        Return the human-readable name of this validator.
        
        This name is used in reporting which validation rules passed or failed.
        
        Returns:
            str: The validator name (e.g., "Pin Conflicts", "Power Connection")
        """
        raise NotImplementedError("Subclasses must implement get_name()")
    
    @staticmethod
    @abstractmethod
    def get_description() -> str:
        """
        Return a description of what this validator checks.
        
        Returns:
            str: A brief description of the validation rule
        """
        raise NotImplementedError("Subclasses must implement get_description()")
