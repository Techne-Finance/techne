"""
Agent Observability Engine for Techne Finance
Inspired by AWS Bedrock AgentCore Observability

Features:
- Distributed Tracing: Track agent workflows end-to-end
- Span Tracking: Measure timing of each operation
- Metrics Collection: Success/failure rates, latency
- Event Logging: Structured logging for debugging
- Dashboard Data: Aggregated stats for visualization

No external dependencies - fully self-contained!
"""

import asyncio
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from functools import wraps
from contextlib import asynccontextmanager
import logging
import uuid
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Observability")


class SpanStatus(Enum):
    """Status of a span/operation"""
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class AgentType(Enum):
    """Types of agents in the system"""
    SCOUT = "scout"
    GUARDIAN = "guardian"
    ENGINEER = "engineer"
    APPRAISER = "appraiser"
    ARBITRAGEUR = "arbitrageur"
    MERCHANT = "merchant"
    CONCIERGE = "concierge"
    HISTORIAN = "historian"
    SENTINEL = "sentinel"
    MEMORY = "memory"
    COORDINATOR = "coordinator"
    SYSTEM = "system"


@dataclass
class Span:
    """A single traced operation"""
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    agent: str
    operation: str
    status: SpanStatus
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def finish(self, status: SpanStatus = SpanStatus.SUCCESS, error: str = None):
        """Finish the span with final status"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        if error:
            self.error = error


@dataclass
class Trace:
    """A complete trace containing multiple spans"""
    trace_id: str
    root_span_id: str
    agent: str
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    span_count: int = 0
    status: SpanStatus = SpanStatus.RUNNING
    user_id: str = "default"


class ObservabilityEngine:
    """
    Distributed tracing and metrics collection for Techne agents.
    Self-contained, no external dependencies.
    """
    
    def __init__(self, db_path: str = "techne_observability.db"):
        self.db_path = db_path
        self.active_spans: Dict[str, Span] = {}
        self.active_traces: Dict[str, Trace] = {}
        self._init_database()
        logger.info("🔍 Observability Engine initialized")
    
    def _init_database(self):
        """Initialize SQLite database for trace storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                root_span_id TEXT,
                agent TEXT NOT NULL,
                operation TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_duration_ms REAL,
                span_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                user_id TEXT DEFAULT 'default'
            )
        """)
        
        # Spans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                parent_id TEXT,
                agent TEXT NOT NULL,
                operation TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                start_time REAL NOT NULL,
                end_time REAL,
                duration_ms REAL,
                metadata TEXT DEFAULT '{}',
                error TEXT,
                FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
            )
        """)
        
        # Events table (for structured logging)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                span_id TEXT,
                agent TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                level TEXT DEFAULT 'info',
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Metrics table (aggregated stats)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                operation TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_traces_agent ON traces(agent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_trace ON events(trace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_agent ON metrics(agent)")
        
        conn.commit()
        conn.close()
    
    # ==========================================
    # TRACING
    # ==========================================
    
    def start_trace(
        self,
        agent: str,
        operation: str,
        user_id: str = "default",
        metadata: Dict[str, Any] = None
    ) -> str:
        """Start a new trace for an agent operation"""
        trace_id = str(uuid.uuid4())[:16]
        span_id = str(uuid.uuid4())[:16]
        now = datetime.now()
        
        # Create root span
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=None,
            agent=agent,
            operation=operation,
            status=SpanStatus.RUNNING,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        # Create trace
        trace = Trace(
            trace_id=trace_id,
            root_span_id=span_id,
            agent=agent,
            operation=operation,
            start_time=now,
            user_id=user_id
        )
        
        self.active_spans[span_id] = span
        self.active_traces[trace_id] = trace
        
        # Persist
        self._save_trace(trace)
        self._save_span(span)
        
        logger.debug(f"Started trace {trace_id} for {agent}.{operation}")
        return trace_id
    
    def start_span(
        self,
        trace_id: str,
        agent: str,
        operation: str,
        parent_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Start a new span within a trace"""
        span_id = str(uuid.uuid4())[:16]
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            agent=agent,
            operation=operation,
            status=SpanStatus.RUNNING,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        self.active_spans[span_id] = span
        
        # Update trace span count
        if trace_id in self.active_traces:
            self.active_traces[trace_id].span_count += 1
        
        self._save_span(span)
        return span_id
    
    def end_span(
        self,
        span_id: str,
        status: SpanStatus = SpanStatus.SUCCESS,
        error: str = None,
        metadata: Dict[str, Any] = None
    ):
        """End a span with final status"""
        if span_id not in self.active_spans:
            # Try to load from DB
            return
        
        span = self.active_spans[span_id]
        span.finish(status, error)
        
        if metadata:
            span.metadata.update(metadata)
        
        self._update_span(span)
        del self.active_spans[span_id]
        
        # Record latency metric
        self._record_metric(
            agent=span.agent,
            operation=span.operation,
            metric_type="latency_ms",
            value=span.duration_ms
        )
        
        # Record success/failure
        self._record_metric(
            agent=span.agent,
            operation=span.operation,
            metric_type="success" if status == SpanStatus.SUCCESS else "error",
            value=1
        )
    
    def end_trace(
        self,
        trace_id: str,
        status: SpanStatus = SpanStatus.SUCCESS
    ):
        """End a trace and all its spans"""
        if trace_id not in self.active_traces:
            return
        
        trace = self.active_traces[trace_id]
        trace.end_time = datetime.now()
        trace.status = status
        
        start_ts = trace.start_time.timestamp()
        end_ts = trace.end_time.timestamp()
        trace.total_duration_ms = (end_ts - start_ts) * 1000
        
        self._update_trace(trace)
        del self.active_traces[trace_id]
        
        # End root span if still active
        if trace.root_span_id in self.active_spans:
            self.end_span(trace.root_span_id, status)
        
        logger.debug(f"Ended trace {trace_id} ({trace.total_duration_ms:.1f}ms)")
    
    # ==========================================
    # CONTEXT MANAGER FOR EASY TRACING
    # ==========================================
    
    @asynccontextmanager
    async def trace(
        self,
        agent: str,
        operation: str,
        user_id: str = "default",
        metadata: Dict[str, Any] = None
    ):
        """Async context manager for automatic trace handling"""
        trace_id = self.start_trace(agent, operation, user_id, metadata)
        try:
            yield trace_id
            self.end_trace(trace_id, SpanStatus.SUCCESS)
        except Exception as e:
            self.log_error(trace_id, None, agent, str(e), traceback.format_exc())
            self.end_trace(trace_id, SpanStatus.ERROR)
            raise
    
    @asynccontextmanager
    async def span(
        self,
        trace_id: str,
        agent: str,
        operation: str,
        parent_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Async context manager for automatic span handling"""
        span_id = self.start_span(trace_id, agent, operation, parent_id, metadata)
        try:
            yield span_id
            self.end_span(span_id, SpanStatus.SUCCESS)
        except Exception as e:
            self.end_span(span_id, SpanStatus.ERROR, str(e))
            raise
    
    # ==========================================
    # DECORATOR FOR AUTOMATIC TRACING
    # ==========================================
    
    def traced(self, agent: str, operation: str = None):
        """Decorator to automatically trace a function"""
        def decorator(func: Callable):
            op_name = operation or func.__name__
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with self.trace(agent, op_name):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                trace_id = self.start_trace(agent, op_name)
                try:
                    result = func(*args, **kwargs)
                    self.end_trace(trace_id, SpanStatus.SUCCESS)
                    return result
                except Exception as e:
                    self.log_error(trace_id, None, agent, str(e))
                    self.end_trace(trace_id, SpanStatus.ERROR)
                    raise
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    # ==========================================
    # STRUCTURED LOGGING
    # ==========================================
    
    def log_event(
        self,
        agent: str,
        event_type: str,
        message: str,
        trace_id: str = None,
        span_id: str = None,
        level: str = "info",
        metadata: Dict[str, Any] = None
    ):
        """Log a structured event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO events (trace_id, span_id, agent, event_type, message, 
                               timestamp, level, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace_id,
            span_id,
            agent,
            event_type,
            message,
            datetime.now().isoformat(),
            level,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def log_error(
        self,
        trace_id: str,
        span_id: str,
        agent: str,
        error: str,
        stack_trace: str = None
    ):
        """Log an error event"""
        self.log_event(
            agent=agent,
            event_type="error",
            message=error,
            trace_id=trace_id,
            span_id=span_id,
            level="error",
            metadata={"stack_trace": stack_trace} if stack_trace else {}
        )
    
    # ==========================================
    # METRICS
    # ==========================================
    
    def _record_metric(
        self,
        agent: str,
        operation: str,
        metric_type: str,
        value: float
    ):
        """Record a metric value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO metrics (agent, operation, metric_type, value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (agent, operation, metric_type, value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    async def get_agent_metrics(
        self,
        agent: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get aggregated metrics for an agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Get counts
        cursor.execute("""
            SELECT metric_type, COUNT(*), AVG(value), SUM(value)
            FROM metrics
            WHERE agent = ? AND timestamp > ?
            GROUP BY metric_type
        """, (agent, cutoff))
        
        metrics = {}
        for row in cursor.fetchall():
            metrics[row[0]] = {
                "count": row[1],
                "avg": round(row[2], 2) if row[2] else 0,
                "sum": round(row[3], 2) if row[3] else 0
            }
        
        conn.close()
        
        # Calculate success rate
        success = metrics.get("success", {}).get("count", 0)
        errors = metrics.get("error", {}).get("count", 0)
        total = success + errors
        
        return {
            "agent": agent,
            "period_hours": hours,
            "total_operations": total,
            "success_count": success,
            "error_count": errors,
            "success_rate": round(success / total * 100, 1) if total > 0 else 100,
            "avg_latency_ms": metrics.get("latency_ms", {}).get("avg", 0),
            "metrics": metrics
        }
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get aggregated data for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        
        # Get per-agent stats
        cursor.execute("""
            SELECT agent, 
                   COUNT(CASE WHEN metric_type = 'success' THEN 1 END) as success,
                   COUNT(CASE WHEN metric_type = 'error' THEN 1 END) as errors,
                   AVG(CASE WHEN metric_type = 'latency_ms' THEN value END) as avg_latency
            FROM metrics
            WHERE timestamp > ?
            GROUP BY agent
        """, (cutoff_24h,))
        
        agents = []
        for row in cursor.fetchall():
            total = row[1] + row[2]
            agents.append({
                "agent": row[0],
                "success": row[1],
                "errors": row[2],
                "success_rate": round(row[1] / total * 100, 1) if total > 0 else 100,
                "avg_latency_ms": round(row[3], 1) if row[3] else 0
            })
        
        # Get recent traces
        cursor.execute("""
            SELECT trace_id, agent, operation, status, total_duration_ms, start_time
            FROM traces
            ORDER BY start_time DESC
            LIMIT 10
        """)
        
        recent_traces = []
        for row in cursor.fetchall():
            recent_traces.append({
                "trace_id": row[0],
                "agent": row[1],
                "operation": row[2],
                "status": row[3],
                "duration_ms": row[4],
                "timestamp": row[5]
            })
        
        # Get error count
        cursor.execute("""
            SELECT COUNT(*) FROM events 
            WHERE level = 'error' AND timestamp > ?
        """, (cutoff_24h,))
        error_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "period": "24h",
            "agents": agents,
            "recent_traces": recent_traces,
            "total_errors": error_count,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_trace_details(self, trace_id: str) -> Dict[str, Any]:
        """Get detailed view of a trace with all spans"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get trace
        cursor.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,))
        trace_row = cursor.fetchone()
        
        if not trace_row:
            conn.close()
            return None
        
        # Get spans
        cursor.execute("""
            SELECT span_id, parent_id, agent, operation, status, 
                   start_time, end_time, duration_ms, metadata, error
            FROM spans
            WHERE trace_id = ?
            ORDER BY start_time
        """, (trace_id,))
        
        spans = []
        for row in cursor.fetchall():
            spans.append({
                "span_id": row[0],
                "parent_id": row[1],
                "agent": row[2],
                "operation": row[3],
                "status": row[4],
                "duration_ms": row[7],
                "metadata": json.loads(row[8]) if row[8] else {},
                "error": row[9]
            })
        
        # Get events
        cursor.execute("""
            SELECT event_type, message, timestamp, level
            FROM events
            WHERE trace_id = ?
            ORDER BY timestamp
        """, (trace_id,))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "type": row[0],
                "message": row[1],
                "timestamp": row[2],
                "level": row[3]
            })
        
        conn.close()
        
        return {
            "trace_id": trace_id,
            "agent": trace_row[2],
            "operation": trace_row[3],
            "status": trace_row[8],
            "start_time": trace_row[4],
            "end_time": trace_row[5],
            "total_duration_ms": trace_row[6],
            "span_count": len(spans),
            "spans": spans,
            "events": events
        }
    
    # ==========================================
    # PERSISTENCE HELPERS
    # ==========================================
    
    def _save_trace(self, trace: Trace):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO traces (trace_id, root_span_id, agent, operation, 
                               start_time, status, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            trace.trace_id,
            trace.root_span_id,
            trace.agent,
            trace.operation,
            trace.start_time.isoformat(),
            trace.status.value,
            trace.user_id
        ))
        conn.commit()
        conn.close()
    
    def _update_trace(self, trace: Trace):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE traces 
            SET end_time = ?, total_duration_ms = ?, span_count = ?, status = ?
            WHERE trace_id = ?
        """, (
            trace.end_time.isoformat() if trace.end_time else None,
            trace.total_duration_ms,
            trace.span_count,
            trace.status.value,
            trace.trace_id
        ))
        conn.commit()
        conn.close()
    
    def _save_span(self, span: Span):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO spans (span_id, trace_id, parent_id, agent, operation,
                              status, start_time, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            span.span_id,
            span.trace_id,
            span.parent_id,
            span.agent,
            span.operation,
            span.status.value,
            span.start_time,
            json.dumps(span.metadata)
        ))
        conn.commit()
        conn.close()
    
    def _update_span(self, span: Span):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE spans 
            SET end_time = ?, duration_ms = ?, status = ?, error = ?, metadata = ?
            WHERE span_id = ?
        """, (
            span.end_time,
            span.duration_ms,
            span.status.value,
            span.error,
            json.dumps(span.metadata),
            span.span_id
        ))
        conn.commit()
        conn.close()


# ==========================================
# SINGLETON & CONVENIENCE
# ==========================================

observability = ObservabilityEngine()


def traced(agent: str, operation: str = None):
    """Decorator shortcut for tracing"""
    return observability.traced(agent, operation)
