"""
YAML File Watcher Service for Hot Reload.

This service watches YAML configuration files for changes and automatically
reloads them without requiring a service restart.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from datametronome_podium.services.yaml_loader import load_and_parse_yaml, YAMLLoadError
from datametronome_podium.services.env_interpolator import interpolate_yaml_data, InterpolationError

logger = logging.getLogger(__name__)


class ReloadResult:
    """Result of a YAML file reload operation."""
    
    def __init__(
        self,
        success: bool,
        file_path: str,
        staves_count: int = 0,
        clefs_count: int = 0,
        error: Optional[str] = None,
        warnings: List[str] = None
    ):
        self.success = success
        self.file_path = file_path
        self.staves_count = staves_count
        self.clefs_count = clefs_count
        self.error = error
        self.warnings = warnings or []
        self.timestamp = datetime.utcnow()
    
    def __bool__(self):
        return self.success


class YAMLFileHandler(FileSystemEventHandler):
    """File system event handler for YAML files."""
    
    def __init__(self, callback: Callable[[str], None], debounce_seconds: float = 1.0):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._pending_events: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if not event.src_path.endswith(('.yaml', '.yml')):
            return
        
        # Debounce rapid changes
        now = datetime.utcnow()
        file_path = event.src_path
        
        # Check if we should process this event
        if file_path in self._pending_events:
            last_event = self._pending_events[file_path]
            if (now - last_event).total_seconds() < self.debounce_seconds:
                # Too soon, skip
                return
        
        self._pending_events[file_path] = now
        
        # Schedule callback
        logger.info(f"YAML file changed: {file_path}")
        try:
            self.callback(file_path)
        except Exception as e:
            logger.error(f"Error in YAML change callback: {e}")


class YAMLWatcher:
    """Service for watching YAML files and triggering reloads."""
    
    def __init__(self):
        self.observer: Optional[Observer] = None
        self.watched_paths: Set[str] = set()
        self.reload_callback: Optional[Callable[[str], ReloadResult]] = None
        self.debounce_seconds: float = 1.0
    
    def start(self, callback: Callable[[str], ReloadResult]):
        """
        Start watching for YAML file changes.
        
        Args:
            callback: Function to call when a YAML file changes.
                     Should accept file_path and return ReloadResult.
        """
        if self.observer and self.observer.is_alive():
            logger.warning("YAML watcher is already running")
            return
        
        self.reload_callback = callback
        
        self.observer = Observer()
        handler = YAMLFileHandler(self._handle_file_change, self.debounce_seconds)
        
        # Watch all registered paths
        for path in self.watched_paths:
            path_obj = Path(path)
            if path_obj.is_dir():
                self.observer.schedule(handler, str(path_obj), recursive=True)
                logger.info(f"Watching directory: {path}")
            elif path_obj.is_file():
                parent_dir = path_obj.parent
                self.observer.schedule(handler, str(parent_dir), recursive=False)
                logger.info(f"Watching file: {path}")
        
        self.observer.start()
        logger.info("YAML watcher started")
    
    def stop(self):
        """Stop watching for file changes."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("YAML watcher stopped")
    
    def watch_path(self, path: str):
        """
        Add a path to watch list.
        
        Args:
            path: File or directory path to watch
        """
        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"Path does not exist, will watch when created: {path}")
        
        self.watched_paths.add(str(path_obj.absolute()))
        logger.info(f"Added to watch list: {path}")
        
        # If observer is running, add this path
        if self.observer and self.observer.is_alive():
            handler = YAMLFileHandler(self._handle_file_change, self.debounce_seconds)
            if path_obj.is_dir():
                self.observer.schedule(handler, str(path_obj), recursive=True)
            else:
                parent_dir = path_obj.parent
                self.observer.schedule(handler, str(parent_dir), recursive=False)
    
    def unwatch_path(self, path: str):
        """
        Remove a path from watch list.
        
        Args:
            path: File or directory path to stop watching
        """
        path_obj = Path(path)
        abs_path = str(path_obj.absolute())
        
        if abs_path in self.watched_paths:
            self.watched_paths.remove(abs_path)
            logger.info(f"Removed from watch list: {path}")
        else:
            logger.warning(f"Path not in watch list: {path}")
    
    def _handle_file_change(self, file_path: str):
        """Handle file change event."""
        if not self.reload_callback:
            logger.warning("No reload callback registered")
            return
        
        try:
            result = self.reload_callback(file_path)
            if result.success:
                logger.info(
                    f"Successfully reloaded {file_path}: "
                    f"{result.staves_count} staves, {result.clefs_count} clefs"
                )
            else:
                logger.error(f"Failed to reload {file_path}: {result.error}")
        except Exception as e:
            logger.error(f"Error handling file change for {file_path}: {e}")


def reload_yaml_file(file_path: str) -> ReloadResult:
    """
    Reload a YAML file and return the result.
    
    This function loads, interpolates, and parses the YAML file.
    It does NOT automatically apply changes to the database - that should
    be handled by the callback function.
    
    Args:
        file_path: Path to YAML file to reload
        
    Returns:
        ReloadResult with success status and counts
    """
    try:
        # Load and parse YAML
        staves, clefs = load_and_parse_yaml(file_path)
        
        return ReloadResult(
            success=True,
            file_path=file_path,
            staves_count=len(staves),
            clefs_count=len(clefs)
        )
        
    except YAMLLoadError as e:
        return ReloadResult(
            success=False,
            file_path=file_path,
            error=f"YAML load error: {str(e)}"
        )
    except InterpolationError as e:
        return ReloadResult(
            success=False,
            file_path=file_path,
            error=f"Interpolation error: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error reloading {file_path}")
        return ReloadResult(
            success=False,
            file_path=file_path,
            error=f"Unexpected error: {str(e)}"
        )


# Global watcher instance
_watcher: Optional[YAMLWatcher] = None


def get_watcher() -> YAMLWatcher:
    """Get or create the global YAML watcher instance."""
    global _watcher
    if _watcher is None:
        _watcher = YAMLWatcher()
    return _watcher


def watch_yaml_directory(path: str, callback: Optional[Callable[[str], ReloadResult]] = None):
    """
    Watch a directory for YAML file changes.
    
    Args:
        path: Directory path to watch
        callback: Optional callback function (if None, uses default reload)
    """
    watcher = get_watcher()
    watcher.watch_path(path)
    
    if callback and not watcher.observer:
        watcher.start(callback)
    elif not watcher.observer:
        # Use default reload callback
        watcher.start(reload_yaml_file)


def stop_watching():
    """Stop the YAML watcher."""
    global _watcher
    if _watcher:
        _watcher.stop()







