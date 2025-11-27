"""Cache invalidation utilities for embedding cache."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import psycopg


def invalidate_stale_cache(
    conn: psycopg.Connection,
    container_id: Optional[str] = None,
    max_age_hours: int = 24,
) -> int:
    """Remove embedding cache entries older than threshold.
    
    Args:
        conn: Postgres connection
        container_id: Optional container ID to filter by
        max_age_hours: Maximum age in hours before eviction
        
    Returns:
        Number of rows deleted
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    if container_id:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM embedding_cache 
                WHERE container_id = %s 
                AND created_at < %s
                """,
                (container_id, cutoff_time),
            )
            return cur.rowcount
    else:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM embedding_cache 
                WHERE created_at < %s
                """,
                (cutoff_time,),
            )
            return cur.rowcount


def get_cache_stats(conn: psycopg.Connection, container_id: Optional[str] = None) -> dict:
    """Get cache statistics for monitoring.
    
    Args:
        conn: Postgres connection
        container_id: Optional container ID to filter by
        
    Returns:
        Dictionary with total_rows, avg_age_hours, and stale_rows
    """
    base_query = "SELECT COUNT(*), AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/3600) FROM embedding_cache"
    
    if container_id:
        with conn.cursor() as cur:
            cur.execute(
                base_query + " WHERE container_id = %s",
                (container_id,),
            )
            total, avg_age = cur.fetchone()
            
            cur.execute(
                "SELECT COUNT(*) FROM embedding_cache WHERE container_id = %s AND created_at < NOW() - INTERVAL '24 hours'",
                (container_id,),
            )
            stale = cur.fetchone()[0]
    else:
        with conn.cursor() as cur:
            cur.execute(base_query)
            total, avg_age = cur.fetchone()
            
            cur.execute(
                "SELECT COUNT(*) FROM embedding_cache WHERE created_at < NOW() - INTERVAL '24 hours'"
            )
            stale = cur.fetchone()[0]
    
    return {
        "total_rows": total or 0,
        "avg_age_hours": float(avg_age or 0),
        "stale_rows": stale or 0,
    }
