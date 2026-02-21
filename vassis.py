"""
Configuration management for the Virtual Assistant.
Provides centralized configuration with environment variable support.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import yaml


@dataclass
class AssistantConfig:
    """Main configuration class for the virtual assistant."""
    
    # Assistant Identity
    name: str = "Assistant"
    voice_name: str = "en-US-JennyNeural"
    language: str = "en"
    
    # Processing Settings
    use_voice: bool = False
    use_gpu: bool = False
    confidence_threshold: float = 0.7
    
    # Learning Settings
    enable_learning: bool = True
    min_feedback_count: int = 3
    
    # Data Paths
    data_dir: str = "data"
    models_dir: str = "models"
    
    # External Services (API keys loaded from environment)
    weather_api_key: str = ""
    search_api_key: str = ""
    
    # Feature Flags
    enable_reminders: bool = True
    enable_calendar: bool = True
    enable_weather: bool = True
    enable_learning: bool = True
    
    @classmethod
    def load_from_file(cls, config_path: str = "config.yaml") -> "AssistantConfig":
        """Load configuration from YAML file."""
        if not Path(config_path).exists():
            return cls()
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}
        
        # Apply environment variable overrides
        env_overrides = {
            'weather_api_key': os.environ.get('WEATHER_API_KEY', ''),
            'search_api_key': os.environ.get('SEARCH_API_KEY', ''),
        }
        config_data.update({k: v for k, v in env_overrides.items() if v})
        
        return cls(**config_data)
    
    def save_to_file(self, config_path: str = "config.yaml"):
        """Save current configuration to YAML file."""
        config_dict = {
            'name': self.name,
            'voice_name': self.voice_name,
            'language': self.language,
            'use_voice': self.use_voice,
            'use_gpu': self.use_gpu,
            'confidence_threshold': self.confidence_threshold,
            'enable_learning': self.enable_learning,
            'data_dir': self.data_dir,
            'models_dir': self.models_dir,
            'enable_reminders': self.enable_reminders,
            'enable_calendar': self.enable_calendar,
            'enable_weather': self.enable_weather,
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)


class ConfigManager:
    """
    Manages configuration loading, validation, and access.
    Provides a singleton-like interface for configuration access.
    """
    
    _instance: Optional["ConfigManager"] = None
    _config: Optional[AssistantConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = AssistantConfig.load_from_file()
    
    @property
    def config(self) -> AssistantConfig:
        return self._config
    
    def reload(self, config_path: str = "config.yaml"):
        """Reload configuration from file."""
        self._config = AssistantConfig.load_from_file(config_path)
    
    def update(self, **kwargs):
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)


# Global configuration instance
config = ConfigManager()
"""
Time parsing and manipulation utilities for the Virtual Assistant.
Handles natural language time expressions like "tomorrow at 3pm".
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from dateutil import parser
from dateutil.relativedelta import relativedelta
import re


class TimeParser:
    """
    Parses natural language time expressions into datetime objects.
    Supports various formats including relative and absolute times.
    """
    
    # Patterns for common time expressions
    TIME_PATTERNS = [
        # Relative times
        (r'in (\d+) (minutes?|mins?)', lambda m: timedelta(minutes=int(m.group(1)))),
        (r'in (\d+) (hours?|hrs?)', lambda m: timedelta(hours=int(m.group(1)))),
        (r'in (\d+) (days?)', lambda m: timedelta(days=int(m.group(1)))),
        (r'in a (minute|hour|day)', lambda m: self._relative_delta(m.group(1))),
        
        # Daily times
        (r'at (\d{1,2}):(\d{2})\s*(am|pm)?', None),
        (r'at (\d{1,2})\s*(am|pm)', None),
        
        # Day references
        (r'today', lambda m: timedelta(0)),
        (r'tomorrow', lambda m: timedelta(days=1)),
        (r'yesterday', lambda m: timedelta(days=-1)),
        
        # Day of week
        (r'on (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', None),
    ]
    
    @staticmethod
    def _relative_delta(time_unit: str) -> timedelta:
        """Convert relative time unit to timedelta."""
        unit_map = {
            'minute': timedelta(minutes=1),
            'hour': timedelta(hours=1),
            'day': timedelta(days=1),
            'week': timedelta(weeks=1),
        }
        return unit_map.get(time_unit, timedelta(0))
    
    @classmethod
    def parse(cls, time_string: str, reference_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Parse a natural language time expression.
        
        Args:
            time_string: Natural language time expression
            reference_time: Reference time for relative calculations (defaults to now)
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        time_string = time_string.lower().strip()
        
        # Try direct dateutil parsing first
        try:
            parsed = parser.parse(time_string, fuzzy=True, default=reference_time)
            if parsed > reference_time or parsed.date() >= reference_time.date():
                return parsed
        except (ValueError, TypeError):
            pass
        
        # Try pattern-based parsing
        parsed_time = reference_time
        
        # Handle relative patterns
        relative_patterns = [
            (r'in (\d+) minutes?', timedelta(minutes=int)),
            (r'in (\d+) hours?', timedelta(hours=int)),
            (r'in (\d+) days?', timedelta(days=int)),
            (r'in (\d+) weeks?', timedelta(weeks=int)),
            (r'tomorrow', lambda: timedelta(days=1)),
            (r'today', lambda: timedelta(0)),
        ]
        
        for pattern, delta_func in relative_patterns:
            match = re.search(pattern, time_string)
            if match:
                if callable(delta_func):
                    delta = delta_func()
                else:
                    delta = delta_func(match)
                parsed_time += delta
                return parsed_time
        
        # Handle time patterns (e.g., "3pm", "2:30 am")
        time_patterns = [
            (r'(\d{1,2}):(\d{2})\s*(am|pm)?', None),
            (r'(\d{1,2})\s*(am|pm)', None),
        ]
        
        for pattern, _ in time_patterns:
            match = re.search(pattern, time_string)
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if len(match.groups()) > 1 else 0
                    ampm = match.group(3) if len(match.groups()) > 2 else None
                    
                    if ampm:
                        if ampm.lower() == 'pm' and hour != 12:
                            hour += 12
                        elif ampm.lower() == 'am' and hour == 12:
                            hour = 0
                    
                    parsed_time = parsed_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    return parsed_time
                except ValueError:
                    continue
        
        # Handle day of week
        days_of_week = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in days_of_week.items():
            if day_name in time_string:
                current_weekday = reference_time.weekday()
                days_ahead = day_num - current_weekday
                if days_ahead <= 0:
                    days_ahead += 7
                parsed_time += timedelta(days=days_ahead)
                return parsed_time
        
        return None
    
    @classmethod
    def parse_duration(cls, duration_string: str) -> Optional[timedelta]:
        """
        Parse a duration string into a timedelta.
        
        Args:
            duration_string: Duration in natural language (e.g., "2 hours 30 minutes")
            
        Returns:
            timedelta or None if parsing fails
        """
        duration_string = duration_string.lower()
        total_delta = timedelta(0)
        
        patterns = [
            (r'(\d+)\s*(?:hours?|hrs?)', lambda m: timedelta(hours=int(m.group(1)))),
            (r'(\d+)\s*(?:minutes?|mins?)', lambda m: timedelta(minutes=int(m.group(1)))),
            (r'(\d+)\s*(?:seconds?|secs?)', lambda m: timedelta(seconds=int(m.group(1)))),
            (r'(\d+)\s*(?:days?)', lambda m: timedelta(days=int(m.group(1)))),
        ]
        
        for pattern, delta_func in patterns:
            match = re.search(pattern, duration_string)
            if match:
                total_delta += delta_func(match)
        
        return total_delta if total_delta != timedelta(0) else None
    
    @staticmethod
    def format_relative(dt: datetime) -> str:
        """Format a datetime as a relative time string."""
        now = datetime.now()
        diff = dt - now
        
        if diff.total_seconds() < 0:
            return "in the past"
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "in a few seconds"
        if seconds < 3600:
            minutes