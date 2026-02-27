"""Cache manager using joblib and diskcache."""

import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta
import diskcache
import joblib


class CacheManager:
    """
    Cache manager for storing scraped jobs, models, and other data.
    
    Uses diskcache for disk-based key-value storage.
    Supports TTL (time-to-live) for cache expiration.
    """
    
    def __init__(
        self,
        cache_dir: str = "cache",
        ttl_hours: int = 24,
        enabled: bool = True
    ):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache storage
            ttl_hours: Default time-to-live in hours
            enabled: Whether caching is enabled
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.enabled = enabled
        
        if self.enabled:
            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize diskcache
            self._cache = diskcache.Cache(str(self.cache_dir))
        else:
            self._cache = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found or expired
        
        Returns:
            Cached value or default
        """
        if not self.enabled or self._cache is None:
            return default
        
        try:
            value = self._cache.get(key, default=default)
            return value
        except Exception as e:
            print(f"Cache get error for key '{key}': {e}")
            return default
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_hours: Time-to-live in hours (None = use default)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or self._cache is None:
            return False
        
        try:
            ttl = ttl_hours if ttl_hours is not None else self.ttl_hours
            expire_seconds = ttl * 3600
            
            self._cache.set(key, value, expire=expire_seconds)
            return True
        except Exception as e:
            print(f"Cache set error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
        
        Returns:
            True if key existed and was deleted
        """
        if not self.enabled or self._cache is None:
            return False
        
        try:
            return self._cache.delete(key)
        except Exception as e:
            print(f"Cache delete error for key '{key}': {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists and not expired
        """
        if not self.enabled or self._cache is None:
            return False
        
        try:
            return key in self._cache
        except Exception as e:
            print(f"Cache exists error for key '{key}': {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cached data.
        
        Returns:
            True if successful
        """
        if not self.enabled or self._cache is None:
            return False
        
        try:
            self._cache.clear()
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or self._cache is None:
            return {"enabled": False}
        
        try:
            return {
                "enabled": True,
                "size": len(self._cache),
                "volume": self._cache.volume(),
                "directory": str(self.cache_dir)
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}
    
    def save_model(self, key: str, model: Any) -> bool:
        """
        Save ML model using joblib.
        
        Args:
            key: Model identifier
            model: Model object to save
        
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            model_path = self.cache_dir / f"{key}.joblib"
            joblib.dump(model, model_path)
            return True
        except Exception as e:
            print(f"Model save error for '{key}': {e}")
            return False
    
    def load_model(self, key: str) -> Optional[Any]:
        """
        Load ML model using joblib.
        
        Args:
            key: Model identifier
        
        Returns:
            Loaded model or None
        """
        if not self.enabled:
            return None
        
        try:
            model_path = self.cache_dir / f"{key}.joblib"
            if not model_path.exists():
                return None
            
            return joblib.load(model_path)
        except Exception as e:
            print(f"Model load error for '{key}': {e}")
            return None
    
    def model_exists(self, key: str) -> bool:
        """
        Check if model file exists.
        
        Args:
            key: Model identifier
        
        Returns:
            True if model file exists
        """
        if not self.enabled:
            return False
        
        model_path = self.cache_dir / f"{key}.joblib"
        return model_path.exists()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close cache."""
        if self._cache is not None:
            self._cache.close()
    
    def close(self):
        """Close cache connection."""
        if self._cache is not None:
            self._cache.close()
