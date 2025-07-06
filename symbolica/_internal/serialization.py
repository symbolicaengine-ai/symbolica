"""
Rule Serialization System
========================

Comprehensive serialization and loading system for rule packs with:
- Hot-reload capabilities
- Version compatibility checking
- Efficient binary and JSON formats
- Cache management and invalidation
- Metadata preservation
"""

import json
import pickle
import hashlib
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import gzip

from ..core import Rule, RuleSet, SymbolicaError, LoadError


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    BINARY = "binary"
    COMPRESSED_JSON = "compressed_json"
    COMPRESSED_BINARY = "compressed_binary"


@dataclass
class PackMetadata:
    """Metadata for serialized rule packs."""
    version: str = "1.0.0"
    format: str = SerializationFormat.JSON.value
    created_at: float = 0.0
    rule_count: int = 0
    content_hash: str = ""
    symbolica_version: str = "1.0.0"
    compression: bool = False
    dag_enabled: bool = True
    optimization_level: str = "default"
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


@dataclass
class LoadResult:
    """Result of loading a rule pack."""
    success: bool
    rule_set: Optional[RuleSet]
    metadata: Optional[PackMetadata]
    errors: List[str]
    load_time_ms: float
    from_cache: bool = False


class RulePackSerializer:
    """
    Comprehensive rule pack serializer with multiple format support.
    
    Features:
    - Multiple serialization formats (JSON, binary, compressed)
    - Version compatibility checking
    - Metadata preservation
    - Content-based integrity checking
    """
    
    def __init__(self, default_format: SerializationFormat = SerializationFormat.JSON):
        self.default_format = default_format
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.RLock()
    
    def serialize(self, rule_set: RuleSet, 
                 output_path: Optional[Path] = None,
                 format: Optional[SerializationFormat] = None,
                 compression: bool = False,
                 include_metadata: bool = True) -> Dict[str, Any]:
        """
        Serialize rule set to specified format.
        
        Args:
            rule_set: RuleSet to serialize
            output_path: Optional path to save to
            format: Serialization format (defaults to instance default)
            compression: Whether to compress the output
            include_metadata: Whether to include metadata
            
        Returns:
            Serialized data dictionary
        """
        if format is None:
            format = self.default_format
        
        start_time = time.perf_counter()
        
        try:
            # Create metadata
            metadata = None
            if include_metadata:
                # Calculate content hash
                rule_content = self._rules_to_hashable(rule_set.rules)
                content_hash = hashlib.sha256(str(rule_content).encode()).hexdigest()
                
                metadata = PackMetadata(
                    format=format.value,
                    rule_count=rule_set.rule_count,
                    content_hash=content_hash,
                    compression=compression,
                    optimization_level=rule_set.metadata.get('optimization_level', 'default')
                )
            
            # Serialize rules
            serialized_rules = self._serialize_rules(rule_set.rules)
            
            # Create pack data
            pack_data = {
                "metadata": asdict(metadata) if metadata else None,
                "rules": serialized_rules,
                "rule_metadata": rule_set.metadata,
                "format_version": "1.0"
            }
            
            # Apply format-specific serialization
            if format in [SerializationFormat.JSON, SerializationFormat.COMPRESSED_JSON]:
                serialized_data = self._serialize_json(pack_data)
                if format == SerializationFormat.COMPRESSED_JSON or compression:
                    serialized_data = self._compress_data(serialized_data)
            
            elif format in [SerializationFormat.BINARY, SerializationFormat.COMPRESSED_BINARY]:
                serialized_data = self._serialize_binary(pack_data)
                if format == SerializationFormat.COMPRESSED_BINARY or compression:
                    serialized_data = self._compress_data(serialized_data)
            
            else:
                raise LoadError(f"Unsupported serialization format: {format}")
            
            # Save to file if path provided
            if output_path:
                self._save_to_file(serialized_data, output_path, format, compression)
            
            # Cache the result
            cache_key = self._generate_cache_key(pack_data)
            with self._cache_lock:
                self._cache[cache_key] = {
                    'rule_set': rule_set,
                    'metadata': metadata,
                    'timestamp': time.time()
                }
            
            serialization_time = (time.perf_counter() - start_time) * 1000
            
            return {
                'success': True,
                'metadata': metadata,
                'serialization_time_ms': serialization_time,
                'size_bytes': len(serialized_data) if isinstance(serialized_data, (bytes, str)) else 0,
                'format': format.value,
                'compressed': compression
            }
            
        except Exception as e:
            raise LoadError(f"Serialization failed: {e}") from e
    
    def deserialize(self, source: Union[Path, str, bytes, Dict[str, Any]],
                   format: Optional[SerializationFormat] = None,
                   validate_version: bool = True,
                   use_cache: bool = True) -> LoadResult:
        """
        Deserialize rule set from various sources.
        
        Args:
            source: Path, raw data, or dictionary to deserialize from
            format: Expected format (auto-detected if None)
            validate_version: Whether to validate version compatibility
            use_cache: Whether to use cached results
            
        Returns:
            LoadResult with deserialized rule set and metadata
        """
        start_time = time.perf_counter()
        errors = []
        
        try:
            # Load raw data
            if isinstance(source, Path):
                raw_data, detected_format = self._load_from_file(source, format)
            elif isinstance(source, (str, bytes)):
                raw_data = source
                detected_format = format or self._detect_format(raw_data)
            elif isinstance(source, dict):
                raw_data = source
                detected_format = SerializationFormat.JSON
            else:
                raise LoadError(f"Unsupported source type: {type(source)}")
            
            # Check cache
            if use_cache and isinstance(source, Path):
                cache_result = self._check_cache(source)
                if cache_result:
                    load_time = (time.perf_counter() - start_time) * 1000
                    return LoadResult(
                        success=True,
                        rule_set=cache_result['rule_set'],
                        metadata=cache_result['metadata'],
                        errors=[],
                        load_time_ms=load_time,
                        from_cache=True
                    )
            
            # Deserialize based on format
            if detected_format in [SerializationFormat.JSON, SerializationFormat.COMPRESSED_JSON]:
                pack_data = self._deserialize_json(raw_data, detected_format)
            elif detected_format in [SerializationFormat.BINARY, SerializationFormat.COMPRESSED_BINARY]:
                pack_data = self._deserialize_binary(raw_data, detected_format)
            else:
                raise LoadError(f"Unsupported format: {detected_format}")
            
            # Extract metadata
            metadata = None
            if pack_data.get('metadata'):
                metadata = PackMetadata(**pack_data['metadata'])
                
                # Validate version compatibility
                if validate_version:
                    version_errors = self._validate_version(metadata)
                    errors.extend(version_errors)
            
            # Deserialize rules
            rules = self._deserialize_rules(pack_data.get('rules', []))
            
            # Create rule set
            rule_metadata = pack_data.get('rule_metadata', {})
            rule_set = RuleSet(rules, rule_metadata)
            
            # Validate content integrity
            if metadata and metadata.content_hash:
                rule_content = self._rules_to_hashable(rules)
                actual_hash = hashlib.sha256(str(rule_content).encode()).hexdigest()
                if actual_hash != metadata.content_hash:
                    errors.append("Content hash mismatch - data may be corrupted")
            
            # Cache the result
            if use_cache and isinstance(source, Path):
                cache_key = str(source.absolute())
                with self._cache_lock:
                    self._cache[cache_key] = {
                        'rule_set': rule_set,
                        'metadata': metadata,
                        'timestamp': time.time(),
                        'file_mtime': source.stat().st_mtime
                    }
            
            load_time = (time.perf_counter() - start_time) * 1000
            
            return LoadResult(
                success=len(errors) == 0,
                rule_set=rule_set,
                metadata=metadata,
                errors=errors,
                load_time_ms=load_time,
                from_cache=False
            )
            
        except Exception as e:
            load_time = (time.perf_counter() - start_time) * 1000
            return LoadResult(
                success=False,
                rule_set=None,
                metadata=None,
                errors=[f"Deserialization failed: {e}"],
                load_time_ms=load_time,
                from_cache=False
            )
    
    def _serialize_rules(self, rules: List[Rule]) -> List[Dict[str, Any]]:
        """Serialize rules to dictionary format."""
        serialized = []
        
        for rule in rules:
            rule_data = {
                "id": rule.id.value,
                "priority": rule.priority.value,
                "condition": {
                    "expression": rule.condition.expression,
                    "content_hash": rule.condition.content_hash,
                    "referenced_fields": list(rule.condition.referenced_fields)
                },
                "actions": [
                    {
                        "type": action.type,
                        "parameters": action.parameters
                    }
                    for action in rule.actions
                ],
                "tags": list(rule.tags),
                "written_fields": list(rule.written_fields)
            }
            serialized.append(rule_data)
        
        return serialized
    
    def _deserialize_rules(self, serialized_rules: List[Dict[str, Any]]) -> List[Rule]:
        """Deserialize rules from dictionary format."""
        from ..core import rule_id, priority, condition, Action
        
        rules = []
        
        for rule_data in serialized_rules:
            # Recreate rule components
            rule_id_obj = rule_id(rule_data["id"])
            priority_obj = priority(rule_data["priority"])
            condition_obj = condition(rule_data["condition"]["expression"])
            
            # Restore referenced fields if available
            if rule_data["condition"].get("referenced_fields"):
                object.__setattr__(condition_obj, 'referenced_fields', 
                                 frozenset(rule_data["condition"]["referenced_fields"]))
            
            # Recreate actions
            actions = [
                Action(action_data["type"], action_data["parameters"])
                for action_data in rule_data["actions"]
            ]
            
            # Recreate rule
            rule = Rule(
                id=rule_id_obj,
                priority=priority_obj,
                condition=condition_obj,
                actions=actions,
                tags=frozenset(rule_data.get("tags", []))
            )
            
            rules.append(rule)
        
        return rules
    
    def _serialize_json(self, data: Dict[str, Any]) -> str:
        """Serialize to JSON string."""
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _deserialize_json(self, data: Union[str, bytes], format: SerializationFormat) -> Dict[str, Any]:
        """Deserialize from JSON string or bytes."""
        if format == SerializationFormat.COMPRESSED_JSON:
            data = self._decompress_data(data)
        
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        return json.loads(data)
    
    def _serialize_binary(self, data: Dict[str, Any]) -> bytes:
        """Serialize to binary format using pickle."""
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    
    def _deserialize_binary(self, data: Union[str, bytes], format: SerializationFormat) -> Dict[str, Any]:
        """Deserialize from binary format."""
        if format == SerializationFormat.COMPRESSED_BINARY:
            data = self._decompress_data(data)
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return pickle.loads(data)
    
    def _compress_data(self, data: Union[str, bytes]) -> bytes:
        """Compress data using gzip."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return gzip.compress(data)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress gzipped data."""
        return gzip.decompress(data)
    
    def _save_to_file(self, data: Union[str, bytes], path: Path, 
                     format: SerializationFormat, compressed: bool) -> None:
        """Save serialized data to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(data, str):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data)
        else:
            with open(path, 'wb') as f:
                f.write(data)
    
    def _load_from_file(self, path: Path, expected_format: Optional[SerializationFormat]) -> tuple:
        """Load and return raw data from file with format detection."""
        if not path.exists():
            raise LoadError(f"File not found: {path}")
        
        # Try to detect format from extension
        detected_format = expected_format
        if detected_format is None:
            if path.suffix.lower() == '.json':
                detected_format = SerializationFormat.JSON
            elif path.suffix.lower() in ['.pkl', '.pickle']:
                detected_format = SerializationFormat.BINARY
            elif path.suffix.lower() == '.gz':
                # Check inner extension
                inner_name = path.stem
                if inner_name.endswith('.json'):
                    detected_format = SerializationFormat.COMPRESSED_JSON
                else:
                    detected_format = SerializationFormat.COMPRESSED_BINARY
            else:
                detected_format = SerializationFormat.JSON  # Default
        
        # Load based on detected format
        if detected_format in [SerializationFormat.JSON, SerializationFormat.COMPRESSED_JSON]:
            if detected_format == SerializationFormat.COMPRESSED_JSON:
                with open(path, 'rb') as f:
                    data = f.read()
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
        else:
            with open(path, 'rb') as f:
                data = f.read()
        
        return data, detected_format
    
    def _detect_format(self, data: Union[str, bytes]) -> SerializationFormat:
        """Detect serialization format from data."""
        if isinstance(data, str):
            # Try to parse as JSON
            try:
                json.loads(data)
                return SerializationFormat.JSON
            except:
                pass
        
        if isinstance(data, bytes):
            # Check if it's compressed
            try:
                decompressed = gzip.decompress(data)
                # Check if decompressed data is JSON
                try:
                    json.loads(decompressed.decode('utf-8'))
                    return SerializationFormat.COMPRESSED_JSON
                except:
                    return SerializationFormat.COMPRESSED_BINARY
            except:
                # Try as pickle
                try:
                    pickle.loads(data)
                    return SerializationFormat.BINARY
                except:
                    pass
        
        # Default fallback
        return SerializationFormat.JSON
    
    def _validate_version(self, metadata: PackMetadata) -> List[str]:
        """Validate version compatibility."""
        errors = []
        
        # Check format version
        if metadata.version != "1.0.0":
            errors.append(f"Unsupported pack version: {metadata.version}")
        
        # Could add more version checks here
        
        return errors
    
    def _check_cache(self, path: Path) -> Optional[Dict[str, Any]]:
        """Check if cached version is still valid."""
        cache_key = str(path.absolute())
        
        with self._cache_lock:
            if cache_key not in self._cache:
                return None
            
            cached = self._cache[cache_key]
            
            # Check if file was modified
            try:
                current_mtime = path.stat().st_mtime
                cached_mtime = cached.get('file_mtime', 0)
                
                if current_mtime != cached_mtime:
                    # File was modified, invalidate cache
                    del self._cache[cache_key]
                    return None
                
                return cached
                
            except (OSError, KeyError):
                # File doesn't exist or cache corrupted
                del self._cache[cache_key]
                return None
    
    def _generate_cache_key(self, data: Dict[str, Any]) -> str:
        """Generate cache key for data."""
        content = json.dumps(data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _rules_to_hashable(self, rules: List[Rule]) -> List[tuple]:
        """Convert rules to hashable format for integrity checking."""
        hashable = []
        for rule in rules:
            rule_tuple = (
                rule.id.value,
                rule.priority.value,
                rule.condition.expression,
                tuple((a.type, tuple(sorted(a.parameters.items()))) for a in rule.actions),
                tuple(sorted(rule.tags))
            )
            hashable.append(rule_tuple)
        return hashable
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self._cache_lock:
            self._cache.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about current cache state."""
        with self._cache_lock:
            return {
                'cached_items': len(self._cache),
                'cache_keys': list(self._cache.keys())
            }


class HotReloadManager:
    """
    Manages hot-reloading of rule packs with file watching.
    
    Features:
    - File system monitoring
    - Automatic reload on changes
    - Callback system for reload events
    - Error handling and recovery
    """
    
    def __init__(self, serializer: Optional[RulePackSerializer] = None):
        self.serializer = serializer or RulePackSerializer()
        self._watched_files: Dict[str, Dict[str, Any]] = {}
        self._callbacks: List[Callable] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def watch_file(self, path: Path, reload_callback: Optional[Callable] = None) -> None:
        """
        Start watching a file for changes.
        
        Args:
            path: Path to watch
            reload_callback: Optional callback for when file changes
        """
        path_str = str(path.absolute())
        
        if not path.exists():
            raise LoadError(f"Cannot watch non-existent file: {path}")
        
        self._watched_files[path_str] = {
            'path': path,
            'last_mtime': path.stat().st_mtime,
            'callback': reload_callback,
            'last_successful_load': None,
            'error_count': 0
        }
        
        if not self._monitoring:
            self._start_monitoring()
    
    def unwatch_file(self, path: Path) -> None:
        """Stop watching a file."""
        path_str = str(path.absolute())
        if path_str in self._watched_files:
            del self._watched_files[path_str]
    
    def add_global_callback(self, callback: Callable) -> None:
        """Add a callback that's called for any file reload."""
        self._callbacks.append(callback)
    
    def _start_monitoring(self) -> None:
        """Start the file monitoring thread."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._check_files()
                time.sleep(1.0)  # Check every second
            except Exception as e:
                # Log error but continue monitoring
                print(f"File monitoring error: {e}")
    
    def _check_files(self) -> None:
        """Check all watched files for changes."""
        for path_str, watch_info in list(self._watched_files.items()):
            try:
                path = watch_info['path']
                
                if not path.exists():
                    continue
                
                current_mtime = path.stat().st_mtime
                last_mtime = watch_info['last_mtime']
                
                if current_mtime != last_mtime:
                    # File changed, attempt reload
                    self._handle_file_change(path_str, watch_info)
                    
            except Exception as e:
                # Handle individual file errors
                watch_info['error_count'] += 1
                if watch_info['error_count'] > 5:
                    # Too many errors, stop watching this file
                    del self._watched_files[path_str]
    
    def _handle_file_change(self, path_str: str, watch_info: Dict[str, Any]) -> None:
        """Handle a file change event."""
        path = watch_info['path']
        
        try:
            # Attempt to reload
            result = self.serializer.deserialize(path, use_cache=False)
            
            if result.success:
                watch_info['last_mtime'] = path.stat().st_mtime
                watch_info['last_successful_load'] = time.time()
                watch_info['error_count'] = 0
                
                # Call specific callback
                if watch_info['callback']:
                    watch_info['callback'](path, result.rule_set, result.metadata)
                
                # Call global callbacks
                for callback in self._callbacks:
                    callback(path, result.rule_set, result.metadata)
            
            else:
                watch_info['error_count'] += 1
                # Could log errors here
                
        except Exception as e:
            watch_info['error_count'] += 1
            # Could log exception here
    
    def stop_monitoring(self) -> None:
        """Stop file monitoring."""
        if self._monitoring:
            self._stop_event.set()
            if self._monitor_thread:
                self._monitor_thread.join(timeout=2.0)
            self._monitoring = False
    
    def get_watch_status(self) -> Dict[str, Any]:
        """Get current watch status."""
        return {
            'monitoring': self._monitoring,
            'watched_files': len(self._watched_files),
            'files': {
                path: {
                    'last_mtime': info['last_mtime'],
                    'error_count': info['error_count'],
                    'last_successful_load': info.get('last_successful_load')
                }
                for path, info in self._watched_files.items()
            }
        }


# Convenience functions
def save_rules(rule_set: RuleSet, path: Path, 
               format: SerializationFormat = SerializationFormat.JSON,
               compress: bool = False) -> Dict[str, Any]:
    """Save rule set to file."""
    serializer = RulePackSerializer()
    return serializer.serialize(rule_set, path, format, compress)


def load_rules(path: Path, 
               validate_version: bool = True,
               use_cache: bool = True) -> LoadResult:
    """Load rule set from file."""
    serializer = RulePackSerializer()
    return serializer.deserialize(path, validate_version=validate_version, use_cache=use_cache)


def create_hot_reload_manager() -> HotReloadManager:
    """Create hot reload manager."""
    return HotReloadManager() 