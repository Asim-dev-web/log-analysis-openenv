"""Scenarios for the Log Analysis Environment."""

ALL_ROOT_CAUSES = [
    "database_max_connections",
    "database_connection_timeout",
    "database_slow_query",
    "database_deadlock",
    "database_disk_full",
    "redis_oom",
    "redis_connection_pool_exhausted",
    "cache_miss_storm",
    "network_timeout",
    "network_partition",
    "dns_resolution_failure",
    "ssl_certificate_expired",
    "memory_leak",
    "memory_oom_killed",
    "cpu_throttling",
    "disk_full",
    "thread_pool_exhausted",
    "null_pointer_exception",
    "configuration_error",
    "bad_deployment",
]

ALL_RECOMMENDED_ACTIONS = [
    "increase_connection_pool_size",
    "restart_service",
    "scale_horizontally",
    "increase_memory_limit",
    "rollback_deployment",
    "clear_disk_space",
    "clear_cache",
    "renew_ssl_certificate",
    "fix_dns_config",
    "increase_thread_pool_size",
    "optimize_slow_queries",
    "enable_rate_limiting",
]

# ============================================================
# EASY SCENARIO
# ============================================================
SCENARIO_DATABASE_OVERLOAD = {
    "id": "database_overload",
    "name": "Database Connection Pool Exhausted",
    "difficulty": "easy",
    "alert": {
        "title": "High error rate on api-gateway (5xx: 23%)",
        "severity": "critical"
    },
    "services": ["api-gateway", "user-service", "database"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Received request GET /users/123",
            "[10:23:45] ERROR: Upstream timeout waiting for user-service (30s)",
            "[10:23:46] ERROR: Upstream timeout waiting for user-service (30s)",
            "[10:23:47] WARN: High error rate detected: 23%",
        ],
        "user-service": [
            "[10:23:44] INFO: Processing request for user 123",
            "[10:23:44] ERROR: Failed to connect to database: connection refused",
            "[10:23:45] ERROR: Database connection pool exhausted",
            "[10:23:46] ERROR: Failed to connect to database: connection refused",
        ],
        "database": [
            "[10:23:40] WARN: Connection pool usage at 95%",
            "[10:23:42] ERROR: Max connections reached (100/100)",
            "[10:23:43] ERROR: Rejecting new connection from 10.0.1.15",
            "[10:23:44] ERROR: Rejecting new connection from 10.0.1.16",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 45.2, "memory_usage": 62.0, "error_rate": 23.0, "latency_p99": 30000},
        "user-service": {"cpu_usage": 32.1, "memory_usage": 58.0, "error_rate": 85.0, "latency_p99": 30000},
        "database": {"cpu_usage": 78.5, "memory_usage": 45.0, "connections_active": 100, "threads_active": 95},
    },
    "ground_truth": {
        "root_cause": "database_max_connections",
        "severity": "critical",
        "affected_services": ["database", "user-service", "api-gateway"],
        "recommended_action": "increase_connection_pool_size",
    },
}

# ============================================================
# MEDIUM SCENARIO
# ============================================================
SCENARIO_REDIS_CASCADE = {
    "id": "redis_cascade",
    "name": "Redis OOM Causing Cascade Failure",
    "difficulty": "medium",
    "alert": {
        "title": "High latency on checkout-service (p99: 8500ms)",
        "severity": "high"
    },
    "services": ["checkout-service", "inventory-service", "redis", "payment-service"],
    "logs": {
        "checkout-service": [
            "[10:23:45] INFO: Processing checkout for order 456",
            "[10:23:46] WARN: Slow response from inventory-service (2340ms)",
            "[10:23:47] ERROR: Timeout waiting for inventory-service",
            "[10:23:48] WARN: Memory usage high (78%)",  # RED HERRING
        ],
        "inventory-service": [
            "[10:23:44] INFO: Checking stock for SKU-1234",
            "[10:23:44] WARN: Cache miss for SKU-1234",
            "[10:23:45] INFO: Querying database for inventory...",
            "[10:23:47] ERROR: Redis connection failed: OOM command not allowed",
        ],
        "redis": [
            "[10:23:30] WARN: Memory usage at 95%",
            "[10:23:35] ERROR: OOM - cannot allocate memory",
            "[10:23:40] ERROR: Evicting keys aggressively",
            "[10:23:42] ERROR: OOM command not allowed when used memory > maxmemory",
        ],
        "payment-service": [
            "[10:23:45] INFO: Payment processed successfully",  # RED HERRING
            "[10:23:46] WARN: SSL certificate expiring in 7 days",  # RED HERRING
        ],
    },
    "metrics": {
        "checkout-service": {"cpu_usage": 45.0, "memory_usage": 78.0, "error_rate": 15.0, "latency_p99": 8500},
        "inventory-service": {"cpu_usage": 52.0, "memory_usage": 65.0, "error_rate": 45.0, "latency_p99": 5000},
        "redis": {"cpu_usage": 30.0, "memory_usage": 99.0, "connections_active": 450, "threads_active": 4},
        "payment-service": {"cpu_usage": 25.0, "memory_usage": 45.0, "error_rate": 0.1, "latency_p99": 200},
    },
    "ground_truth": {
        "root_cause": "redis_oom",
        "severity": "high",
        "affected_services": ["redis", "inventory-service", "checkout-service"],
        "recommended_action": "increase_memory_limit",
    },
}

# ============================================================
# HARD SCENARIO
# ============================================================
SCENARIO_INTERMITTENT_THREAD_POOL = {
    "id": "intermittent_thread_pool",
    "name": "Batch Job Saturating Thread Pool",
    "difficulty": "hard",
    "alert": {
        "title": "Intermittent 503s on api-gateway (error rate fluctuating 0-15%)",
        "severity": "medium"
    },
    "services": ["api-gateway", "user-service-1", "user-service-2", "user-service-3", "batch-processor", "load-balancer"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Request handled successfully (45ms)",
            "[10:23:46] INFO: Request handled successfully (52ms)",
            "[10:23:47] ERROR: Upstream connection failed to user-service-3",
            "[10:23:48] INFO: Request handled successfully (48ms)",
            "[10:23:49] INFO: Request handled successfully (41ms)",
            "[10:23:50] ERROR: Upstream connection failed to user-service-3",
        ],
        "user-service-1": [
            "[10:23:45] INFO: Health check passed",
            "[10:23:50] INFO: Request processed (42ms)",
        ],
        "user-service-2": [
            "[10:23:45] INFO: Health check passed",
            "[10:23:50] INFO: Request processed (38ms)",
        ],
        "user-service-3": [
            "[10:23:45] INFO: Health check passed",  # PASSES HEALTH CHECK!
            "[10:23:47] ERROR: Thread pool exhausted, rejecting request",
            "[10:23:48] INFO: Health check passed",  # STILL PASSES!
            "[10:23:50] ERROR: Thread pool exhausted, rejecting request",
            "[10:23:55] INFO: Thread pool recovered (12/100 active)",
        ],
        "batch-processor": [
            "[10:22:00] INFO: Starting large batch job",
            "[10:22:30] INFO: Spawning 80 worker threads",
            "[10:23:00] INFO: Workers connecting to user-service-3 (sticky session)",
            "[10:23:30] INFO: Processing 50000 records...",
        ],
        "load-balancer": [
            "[10:23:00] INFO: Health check config: endpoint=/health, interval=30s",
            "[10:23:30] INFO: All backends healthy",  # MISLEADING
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 8.0, "latency_p99": 500},
        "user-service-1": {"cpu_usage": 40.0, "memory_usage": 55.0, "error_rate": 0.0, "threads_active": 25},
        "user-service-2": {"cpu_usage": 38.0, "memory_usage": 52.0, "error_rate": 0.0, "threads_active": 22},
        "user-service-3": {"cpu_usage": 45.0, "memory_usage": 62.0, "error_rate": 35.0, "threads_active": 98},
        "batch-processor": {"cpu_usage": 85.0, "memory_usage": 70.0, "error_rate": 0.0, "threads_active": 80},
        "load-balancer": {"cpu_usage": 15.0, "memory_usage": 30.0, "error_rate": 0.0, "connections_active": 1500},
    },
    "ground_truth": {
        "root_cause": "thread_pool_exhausted",
        "severity": "medium",
        "affected_services": ["batch-processor", "user-service-3", "api-gateway"],
        "recommended_action": "increase_thread_pool_size",
    },
}

# ============================================================
# ALL SCENARIOS
# ============================================================
ALL_SCENARIOS = [
    SCENARIO_DATABASE_OVERLOAD,
    SCENARIO_REDIS_CASCADE,
    SCENARIO_INTERMITTENT_THREAD_POOL,
]

SCENARIOS_BY_DIFFICULTY = {
    "easy": [s for s in ALL_SCENARIOS if s["difficulty"] == "easy"],
    "medium": [s for s in ALL_SCENARIOS if s["difficulty"] == "medium"],
    "hard": [s for s in ALL_SCENARIOS if s["difficulty"] == "hard"],
}