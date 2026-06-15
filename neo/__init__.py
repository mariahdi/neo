"""Neo — a personal operating system. The orchestration layer.

Public surface:
    from neo import NeoLoop, Config, WorkItem, Category, State
"""
from .config import Config
from .loop import NeoLoop
from .types import Category, State, WorkItem

__all__ = ["NeoLoop", "Config", "WorkItem", "Category", "State"]
__version__ = "0.0.1"
