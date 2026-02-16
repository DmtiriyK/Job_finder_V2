"""Rate limiter for scrapers to avoid being blocked."""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class RateLimitState:
    """State for rate limiting a specific resource."""
    
    last_request_time: Optional[float] = None
    request_count: int = 0
    window_start: Optional[datetime] = None


class RateLimiter:
    """
    Rate limiter to control request frequency to avoid being blocked.
    
    Supports:
    - Minimum delay between requests
    - Request count limits per time window
    - Per-source rate limiting
    """
    
    def __init__(
        self,
        min_delay_seconds: float = 2.0,
        max_requests_per_minute: Optional[int] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            min_delay_seconds: Minimum delay between requests in seconds
            max_requests_per_minute: Maximum requests per minute (None = unlimited)
        """
        self.min_delay_seconds = min_delay_seconds
        self.max_requests_per_minute = max_requests_per_minute
        self._states: Dict[str, RateLimitState] = {}
        self._lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None
    
    def _get_state(self, source: str) -> RateLimitState:
        """
        Get or create rate limit state for a source.
        
        Args:
            source: Source identifier
        
        Returns:
            RateLimitState for the source
        """
        if source not in self._states:
            self._states[source] = RateLimitState()
        return self._states[source]
    
    def wait(self, source: str = "default") -> None:
        """
        Wait if necessary to respect rate limits (blocking).
        
        Args:
            source: Source identifier for per-source rate limiting
        """
        state = self._get_state(source)
        now = time.time()
        
        # Check minimum delay
        if state.last_request_time is not None:
            elapsed = now - state.last_request_time
            if elapsed < self.min_delay_seconds:
                wait_time = self.min_delay_seconds - elapsed
                time.sleep(wait_time)
        
        # Check rate limit per minute
        if self.max_requests_per_minute is not None:
            now_dt = datetime.now()
            
            # Reset window if needed
            if state.window_start is None or (now_dt - state.window_start) >= timedelta(minutes=1):
                state.window_start = now_dt
                state.request_count = 0
            
            # Wait if limit exceeded
            if state.request_count >= self.max_requests_per_minute:
                window_end = state.window_start + timedelta(minutes=1)
                wait_seconds = (window_end - now_dt).total_seconds()
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                # Reset window
                state.window_start = datetime.now()
                state.request_count = 0
        
        # Update state
        state.last_request_time = time.time()
        state.request_count += 1
    
    async def async_wait(self, source: str = "default") -> None:
        """
        Async version of wait() for use with asyncio.
        
        Args:
            source: Source identifier for per-source rate limiting
        """
        if self._lock is None:
            self._lock = asyncio.Lock()
        
        async with self._lock:
            state = self._get_state(source)
            now = time.time()
            
            # Check minimum delay
            if state.last_request_time is not None:
                elapsed = now - state.last_request_time
                if elapsed < self.min_delay_seconds:
                    wait_time = self.min_delay_seconds - elapsed
                    await asyncio.sleep(wait_time)
            
            # Check rate limit per minute
            if self.max_requests_per_minute is not None:
                now_dt = datetime.now()
                
                # Reset window if needed
                if state.window_start is None or (now_dt - state.window_start) >= timedelta(minutes=1):
                    state.window_start = now_dt
                    state.request_count = 0
                
                # Wait if limit exceeded
                if state.request_count >= self.max_requests_per_minute:
                    window_end = state.window_start + timedelta(minutes=1)
                    wait_seconds = (window_end - now_dt).total_seconds()
                    if wait_seconds > 0:
                        await asyncio.sleep(wait_seconds)
                    # Reset window
                    state.window_start = datetime.now()
                    state.request_count = 0
            
            # Update state
            state.last_request_time = time.time()
            state.request_count += 1
    
    def reset(self, source: Optional[str] = None) -> None:
        """
        Reset rate limit state.
        
        Args:
            source: Source to reset (None = reset all)
        """
        if source is None:
            self._states.clear()
        elif source in self._states:
            del self._states[source]
    
    def get_stats(self, source: str = "default") -> Dict[str, any]:
        """
        Get rate limiting statistics for a source.
        
        Args:
            source: Source identifier
        
        Returns:
            Dictionary with statistics
        """
        if source not in self._states:
            return {
                "total_requests": 0,
                "current_window_requests": 0,
                "last_request": None
            }
        
        state = self._states[source]
        return {
            "total_requests": state.request_count,
            "current_window_requests": state.request_count,
            "last_request": state.last_request_time,
            "window_start": state.window_start
        }
