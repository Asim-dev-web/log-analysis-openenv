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
    "update_configuration",
    "enable_circuit_breaker",
]

# ============================================================
# EASY SCENARIOS (6) - Obvious errors in logs
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

SCENARIO_SSL_EXPIRED = {
    "id": "ssl_certificate_expired",
    "name": "SSL Certificate Expired",
    "difficulty": "easy",
    "alert": {
        "title": "Connection failures to payment-service (100% error rate)",
        "severity": "critical"
    },
    "services": ["api-gateway", "payment-service", "order-service"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Routing request to payment-service",
            "[10:23:45] ERROR: SSL handshake failed with payment-service",
            "[10:23:46] ERROR: certificate has expired",
            "[10:23:47] ERROR: SSL handshake failed with payment-service",
        ],
        "payment-service": [
            "[10:23:45] INFO: Service started on port 443",
            "[10:23:45] WARN: SSL certificate expires in 0 days",
            "[10:23:46] INFO: Incoming connection from api-gateway",
            "[10:23:46] ERROR: TLS handshake error: certificate expired",
        ],
        "order-service": [
            "[10:23:45] INFO: Processing order #12345",
            "[10:23:46] INFO: Calling payment-service for payment",
            "[10:23:47] ERROR: Payment request failed: connection error",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 25.0, "memory_usage": 45.0, "error_rate": 35.0, "latency_p99": 100},
        "payment-service": {"cpu_usage": 5.0, "memory_usage": 30.0, "error_rate": 100.0, "latency_p99": 10},
        "order-service": {"cpu_usage": 40.0, "memory_usage": 55.0, "error_rate": 40.0, "latency_p99": 5000},
    },
    "ground_truth": {
        "root_cause": "ssl_certificate_expired",
        "severity": "critical",
        "affected_services": ["payment-service", "api-gateway", "order-service"],
        "recommended_action": "renew_ssl_certificate",
    },
}

SCENARIO_DISK_FULL = {
    "id": "disk_full",
    "name": "Disk Full on Database Server",
    "difficulty": "easy",
    "alert": {
        "title": "Database write failures (error rate: 100%)",
        "severity": "critical"
    },
    "services": ["api-gateway", "user-service", "database"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Received POST /users/create",
            "[10:23:46] ERROR: Upstream error from user-service: 500",
            "[10:23:47] ERROR: Upstream error from user-service: 500",
        ],
        "user-service": [
            "[10:23:45] INFO: Creating new user record",
            "[10:23:45] ERROR: Database insert failed",
            "[10:23:46] ERROR: DBError: could not write to database",
            "[10:23:47] ERROR: Retrying insert... failed",
        ],
        "database": [
            "[10:23:40] WARN: Disk usage at 98%",
            "[10:23:42] ERROR: No space left on device",
            "[10:23:43] ERROR: Cannot write WAL log: disk full",
            "[10:23:44] ERROR: FATAL: could not write to file: No space left on device",
            "[10:23:45] ERROR: Rejecting all write operations",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 30.0, "memory_usage": 50.0, "error_rate": 45.0, "latency_p99": 200},
        "user-service": {"cpu_usage": 25.0, "memory_usage": 48.0, "error_rate": 100.0, "latency_p99": 100},
        "database": {"cpu_usage": 15.0, "memory_usage": 40.0, "connections_active": 50, "threads_active": 10},
    },
    "ground_truth": {
        "root_cause": "disk_full",
        "severity": "critical",
        "affected_services": ["database", "user-service", "api-gateway"],
        "recommended_action": "clear_disk_space",
    },
}

SCENARIO_CONFIG_ERROR = {
    "id": "configuration_error",
    "name": "Invalid Configuration After Deployment",
    "difficulty": "easy",
    "alert": {
        "title": "notification-service failing to start (restart loop)",
        "severity": "high"
    },
    "services": ["notification-service", "api-gateway", "config-server"],
    "logs": {
        "notification-service": [
            "[10:23:45] INFO: Starting notification-service v2.3.1",
            "[10:23:45] INFO: Loading configuration from config-server",
            "[10:23:46] ERROR: Configuration validation failed",
            "[10:23:46] ERROR: Missing required field: 'smtp.host'",
            "[10:23:47] FATAL: Cannot start service with invalid configuration",
            "[10:23:48] INFO: Service shutting down",
            "[10:23:50] INFO: Starting notification-service v2.3.1 (restart attempt 2)",
        ],
        "api-gateway": [
            "[10:23:45] INFO: Health check for notification-service",
            "[10:23:46] WARN: notification-service health check failed",
            "[10:23:50] WARN: notification-service not responding",
        ],
        "config-server": [
            "[10:23:40] INFO: Serving configuration for notification-service",
            "[10:23:41] INFO: Configuration version: 2.3.1-bad",
            "[10:23:42] WARN: Configuration missing optional field 'smtp.port', using default",
        ],
    },
    "metrics": {
        "notification-service": {"cpu_usage": 5.0, "memory_usage": 10.0, "error_rate": 100.0, "latency_p99": 0},
        "api-gateway": {"cpu_usage": 30.0, "memory_usage": 50.0, "error_rate": 5.0, "latency_p99": 100},
        "config-server": {"cpu_usage": 10.0, "memory_usage": 35.0, "error_rate": 0.0, "latency_p99": 50},
    },
    "ground_truth": {
        "root_cause": "configuration_error",
        "severity": "high",
        "affected_services": ["notification-service", "config-server"],
        "recommended_action": "update_configuration",
    },
}

SCENARIO_NULL_POINTER = {
    "id": "null_pointer_exception",
    "name": "Null Pointer Exception in Production",
    "difficulty": "easy",
    "alert": {
        "title": "cart-service returning 500 errors (100% failure)",
        "severity": "critical"
    },
    "services": ["api-gateway", "cart-service", "product-service"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Request to /cart/add",
            "[10:23:45] ERROR: cart-service returned 500 Internal Server Error",
            "[10:23:46] ERROR: cart-service returned 500 Internal Server Error",
            "[10:23:47] ERROR: cart-service returned 500 Internal Server Error",
        ],
        "cart-service": [
            "[10:23:45] INFO: Adding item to cart",
            "[10:23:45] ERROR: NullPointerException at CartService.java:142",
            "[10:23:45] ERROR: java.lang.NullPointerException: Cannot invoke method on null object",
            "[10:23:45] ERROR: Stack trace: CartService.addItem(CartService.java:142)",
            "[10:23:46] ERROR: NullPointerException at CartService.java:142",
            "[10:23:47] ERROR: Service unhealthy due to repeated exceptions",
        ],
        "product-service": [
            "[10:23:45] INFO: Product lookup successful",
            "[10:23:46] INFO: Returning product details",
            "[10:23:47] INFO: All requests processed normally",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 33.0, "latency_p99": 100},
        "cart-service": {"cpu_usage": 10.0, "memory_usage": 45.0, "error_rate": 100.0, "latency_p99": 50},
        "product-service": {"cpu_usage": 25.0, "memory_usage": 40.0, "error_rate": 0.0, "latency_p99": 80},
    },
    "ground_truth": {
        "root_cause": "null_pointer_exception",
        "severity": "critical",
        "affected_services": ["cart-service", "api-gateway"],
        "recommended_action": "rollback_deployment",
    },
}

SCENARIO_BAD_DEPLOYMENT = {
    "id": "bad_deployment",
    "name": "Bad Deployment Causing Crashes",
    "difficulty": "easy",
    "alert": {
        "title": "auth-service crash loop after deployment",
        "severity": "critical"
    },
    "services": ["api-gateway", "auth-service", "user-service"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Routing to auth-service",
            "[10:23:45] ERROR: auth-service connection refused",
            "[10:23:46] ERROR: auth-service not available",
            "[10:23:50] ERROR: auth-service connection refused",
        ],
        "auth-service": [
            "[10:23:40] INFO: Starting auth-service v2.5.0",
            "[10:23:41] INFO: Deployed version: 2.5.0 (deployed 5 mins ago)",
            "[10:23:42] ERROR: Failed to initialize OAuth provider",
            "[10:23:42] ERROR: Missing required dependency: oauth-lib v2.0",
            "[10:23:43] FATAL: Application startup failed",
            "[10:23:45] INFO: Restarting auth-service v2.5.0 (attempt 2)",
            "[10:23:46] FATAL: Application startup failed",
        ],
        "user-service": [
            "[10:23:45] INFO: Processing user request",
            "[10:23:46] ERROR: Cannot validate token: auth-service unavailable",
            "[10:23:47] WARN: Falling back to cached auth",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 30.0, "memory_usage": 45.0, "error_rate": 40.0, "latency_p99": 200},
        "auth-service": {"cpu_usage": 5.0, "memory_usage": 15.0, "error_rate": 100.0, "latency_p99": 0},
        "user-service": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 25.0, "latency_p99": 500},
    },
    "ground_truth": {
        "root_cause": "bad_deployment",
        "severity": "critical",
        "affected_services": ["auth-service", "api-gateway", "user-service"],
        "recommended_action": "rollback_deployment",
    },
}

# ============================================================
# MEDIUM SCENARIOS (6) - Red herrings, need to correlate
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
            "[10:23:48] WARN: High memory usage detected",
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
            "[10:23:45] INFO: Payment processed successfully",
            "[10:23:46] WARN: SSL certificate expiring in 7 days",
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

SCENARIO_MEMORY_LEAK = {
    "id": "memory_leak",
    "name": "Gradual Memory Leak Causing OOM",
    "difficulty": "medium",
    "alert": {
        "title": "search-service killed by OOM killer",
        "severity": "high"
    },
    "services": ["search-service", "api-gateway", "elasticsearch", "cache-service"],
    "logs": {
        "search-service": [
            "[10:20:00] INFO: Processing search query 'laptop'",
            "[10:20:15] INFO: Processing search query 'phone'",
            "[10:21:00] WARN: GC pause time increasing: 500ms",
            "[10:22:00] WARN: Memory usage at 85%",
            "[10:22:30] WARN: GC pause time: 2000ms",
            "[10:23:00] ERROR: OutOfMemoryError: Java heap space",
            "[10:23:01] FATAL: Process killed by OOM killer",
        ],
        "api-gateway": [
            "[10:23:01] ERROR: Connection refused to search-service",
            "[10:23:02] ERROR: search-service unavailable",
            "[10:23:05] INFO: search-service back online (restarted)",
        ],
        "elasticsearch": [
            "[10:20:00] INFO: Query received from search-service",
            "[10:21:00] INFO: Query response time: 45ms",
            "[10:22:00] INFO: Cluster health: green",
        ],
        "cache-service": [
            "[10:20:00] INFO: Cache hit ratio: 85%",
            "[10:21:00] INFO: Cache hit ratio: 60%",
            "[10:22:00] WARN: Cache evictions increasing",
        ],
    },
    "metrics": {
        "search-service": {"cpu_usage": 90.0, "memory_usage": 99.0, "error_rate": 100.0, "latency_p99": 5000},
        "api-gateway": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 25.0, "latency_p99": 3000},
        "elasticsearch": {"cpu_usage": 40.0, "memory_usage": 60.0, "error_rate": 0.0, "latency_p99": 50},
        "cache-service": {"cpu_usage": 20.0, "memory_usage": 70.0, "error_rate": 0.0, "latency_p99": 10},
    },
    "ground_truth": {
        "root_cause": "memory_leak",
        "severity": "high",
        "affected_services": ["search-service", "api-gateway"],
        "recommended_action": "restart_service",
    },
}

SCENARIO_DNS_FAILURE = {
    "id": "dns_resolution_failure",
    "name": "DNS Resolution Failure After Network Change",
    "difficulty": "medium",
    "alert": {
        "title": "Intermittent connection failures across multiple services",
        "severity": "high"
    },
    "services": ["api-gateway", "user-service", "order-service", "dns-server", "network-monitor"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Routing request to user-service",
            "[10:23:46] ERROR: Could not resolve host: user-service.internal",
            "[10:23:47] INFO: Routing request to order-service",
            "[10:23:47] ERROR: Could not resolve host: order-service.internal",
            "[10:23:48] INFO: Retry successful for user-service",
        ],
        "user-service": [
            "[10:23:45] INFO: Service healthy",
            "[10:23:46] INFO: Processed request successfully",
        ],
        "order-service": [
            "[10:23:45] INFO: Service healthy",
            "[10:23:46] ERROR: Failed to connect to payment-service: DNS lookup failed",
        ],
        "dns-server": [
            "[10:23:00] WARN: High query latency detected",
            "[10:23:30] ERROR: Upstream DNS timeout",
            "[10:23:45] ERROR: Failed to resolve: user-service.internal",
            "[10:23:46] WARN: DNS cache cleared unexpectedly",
        ],
        "network-monitor": [
            "[10:23:00] INFO: Network configuration changed",
            "[10:23:01] INFO: New DNS server: 10.0.0.53",
            "[10:23:30] WARN: Packet loss detected: 5%",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 40.0, "memory_usage": 55.0, "error_rate": 30.0, "latency_p99": 2000},
        "user-service": {"cpu_usage": 25.0, "memory_usage": 45.0, "error_rate": 0.0, "latency_p99": 100},
        "order-service": {"cpu_usage": 30.0, "memory_usage": 50.0, "error_rate": 20.0, "latency_p99": 1500},
        "dns-server": {"cpu_usage": 80.0, "memory_usage": 40.0, "error_rate": 25.0, "latency_p99": 500},
        "network-monitor": {"cpu_usage": 10.0, "memory_usage": 20.0, "error_rate": 0.0, "latency_p99": 10},
    },
    "ground_truth": {
        "root_cause": "dns_resolution_failure",
        "severity": "high",
        "affected_services": ["dns-server", "api-gateway", "order-service"],
        "recommended_action": "fix_dns_config",
    },
}

SCENARIO_SLOW_QUERY = {
    "id": "database_slow_query",
    "name": "Unoptimized Query Causing Timeouts",
    "difficulty": "medium",
    "alert": {
        "title": "High latency on reports-service (p99: 45000ms)",
        "severity": "high"
    },
    "services": ["reports-service", "api-gateway", "database", "cache-service"],
    "logs": {
        "reports-service": [
            "[10:23:45] INFO: Generating monthly sales report",
            "[10:23:46] INFO: Executing query: SELECT * FROM orders JOIN...",
            "[10:24:30] WARN: Query still running after 45s",
            "[10:25:00] ERROR: Query timeout after 60s",
            "[10:25:01] INFO: Retrying with same query...",
        ],
        "api-gateway": [
            "[10:23:45] INFO: Request to /reports/monthly",
            "[10:24:45] WARN: Upstream timeout from reports-service",
            "[10:25:00] ERROR: 504 Gateway Timeout",
        ],
        "database": [
            "[10:23:46] INFO: Executing query from reports-service",
            "[10:23:47] WARN: Full table scan detected on 'orders' table",
            "[10:23:48] WARN: Query using 80% of available memory",
            "[10:24:00] WARN: Slow query log: 15000ms and counting",
            "[10:24:30] ERROR: Query consuming excessive resources",
        ],
        "cache-service": [
            "[10:23:45] INFO: Cache miss for report:monthly:2024",
            "[10:23:46] INFO: Cache hit ratio: 95%",
        ],
    },
    "metrics": {
        "reports-service": {"cpu_usage": 30.0, "memory_usage": 60.0, "error_rate": 80.0, "latency_p99": 45000},
        "api-gateway": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 15.0, "latency_p99": 45000},
        "database": {"cpu_usage": 95.0, "memory_usage": 85.0, "connections_active": 50, "threads_active": 48},
        "cache-service": {"cpu_usage": 15.0, "memory_usage": 40.0, "error_rate": 0.0, "latency_p99": 5},
    },
    "ground_truth": {
        "root_cause": "database_slow_query",
        "severity": "high",
        "affected_services": ["database", "reports-service", "api-gateway"],
        "recommended_action": "optimize_slow_queries",
    },
}

SCENARIO_CACHE_STAMPEDE = {
    "id": "cache_miss_storm",
    "name": "Cache Stampede After TTL Expiry",
    "difficulty": "medium",
    "alert": {
        "title": "Database CPU spike to 100%, multiple service timeouts",
        "severity": "high"
    },
    "services": ["api-gateway", "product-service", "cache", "database"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Request to /products/popular",
            "[10:23:46] WARN: product-service response slow (3500ms)",
            "[10:23:47] ERROR: Timeout from product-service",
            "[10:23:48] ERROR: Multiple timeout errors",
        ],
        "product-service": [
            "[10:23:45] INFO: Fetching popular products",
            "[10:23:45] WARN: Cache miss for popular_products",
            "[10:23:45] INFO: Querying database...",
            "[10:23:46] WARN: Cache miss for popular_products (concurrent request)",
            "[10:23:46] WARN: Cache miss for popular_products (concurrent request)",
            "[10:23:47] ERROR: Database query timeout",
        ],
        "cache": [
            "[10:23:44] INFO: Key popular_products expired (TTL: 3600s)",
            "[10:23:45] INFO: Cache miss: popular_products",
            "[10:23:45] INFO: Cache miss: popular_products",
            "[10:23:45] INFO: Cache miss: popular_products",
            "[10:23:46] WARN: High miss rate detected",
        ],
        "database": [
            "[10:23:45] INFO: Query from product-service",
            "[10:23:45] INFO: Query from product-service (duplicate)",
            "[10:23:45] INFO: Query from product-service (duplicate)",
            "[10:23:46] WARN: CPU at 95%",
            "[10:23:47] ERROR: Too many concurrent queries",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 40.0, "memory_usage": 50.0, "error_rate": 35.0, "latency_p99": 5000},
        "product-service": {"cpu_usage": 60.0, "memory_usage": 55.0, "error_rate": 40.0, "latency_p99": 4000},
        "cache": {"cpu_usage": 20.0, "memory_usage": 45.0, "error_rate": 0.0, "latency_p99": 5},
        "database": {"cpu_usage": 100.0, "memory_usage": 80.0, "connections_active": 95, "threads_active": 95},
    },
    "ground_truth": {
        "root_cause": "cache_miss_storm",
        "severity": "high",
        "affected_services": ["cache", "database", "product-service", "api-gateway"],
        "recommended_action": "enable_rate_limiting",
    },
}

SCENARIO_DEADLOCK = {
    "id": "database_deadlock",
    "name": "Database Deadlock Between Services",
    "difficulty": "medium",
    "alert": {
        "title": "order-service and inventory-service both timing out",
        "severity": "high"
    },
    "services": ["api-gateway", "order-service", "inventory-service", "database"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Request to /orders/create",
            "[10:23:50] WARN: order-service slow response (5000ms)",
            "[10:23:55] ERROR: order-service timeout",
            "[10:23:56] ERROR: inventory-service timeout",
        ],
        "order-service": [
            "[10:23:45] INFO: Creating order #789",
            "[10:23:45] INFO: Acquiring lock on orders table",
            "[10:23:46] INFO: Waiting for inventory lock...",
            "[10:23:50] WARN: Still waiting for inventory lock (5s)",
            "[10:23:55] ERROR: Lock wait timeout exceeded",
        ],
        "inventory-service": [
            "[10:23:45] INFO: Updating inventory for SKU-100",
            "[10:23:45] INFO: Acquiring lock on inventory table",
            "[10:23:46] INFO: Waiting for orders lock...",
            "[10:23:50] WARN: Still waiting for orders lock (5s)",
            "[10:23:55] ERROR: Lock wait timeout exceeded",
        ],
        "database": [
            "[10:23:45] INFO: Transaction started: order-service",
            "[10:23:45] INFO: Transaction started: inventory-service",
            "[10:23:50] WARN: Deadlock detected between transactions",
            "[10:23:55] ERROR: Deadlock victim: transaction rolled back",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 25.0, "latency_p99": 6000},
        "order-service": {"cpu_usage": 20.0, "memory_usage": 45.0, "error_rate": 50.0, "latency_p99": 5500},
        "inventory-service": {"cpu_usage": 20.0, "memory_usage": 45.0, "error_rate": 50.0, "latency_p99": 5500},
        "database": {"cpu_usage": 40.0, "memory_usage": 50.0, "connections_active": 80, "threads_active": 75},
    },
    "ground_truth": {
        "root_cause": "database_deadlock",
        "severity": "high",
        "affected_services": ["database", "order-service", "inventory-service"],
        "recommended_action": "restart_service",
    },
}

# ============================================================
# HARD SCENARIOS (6) - Metrics required, subtle clues
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
            "[10:23:45] INFO: Health check passed",
            "[10:23:47] ERROR: Thread pool exhausted, rejecting request",
            "[10:23:48] INFO: Health check passed",
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
            "[10:23:30] INFO: All backends healthy",
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

SCENARIO_CONNECTION_LEAK = {
    "id": "connection_pool_leak",
    "name": "Connection Pool Leak Under Load",
    "difficulty": "hard",
    "alert": {
        "title": "Gradual increase in database connection errors",
        "severity": "medium"
    },
    "services": ["api-gateway", "order-service", "inventory-service", "database", "monitoring"],
    "logs": {
        "api-gateway": [
            "[10:00:00] INFO: Request processed successfully",
            "[10:30:00] INFO: Request processed successfully",
            "[11:00:00] WARN: Slight increase in latency detected",
            "[11:30:00] ERROR: Timeout waiting for order-service",
        ],
        "order-service": [
            "[10:00:00] INFO: Database connection acquired",
            "[10:00:01] INFO: Order created successfully",
            "[10:30:00] INFO: Database connection acquired",
            "[10:30:01] INFO: Order created successfully",
            "[11:00:00] WARN: Connection pool usage: 80%",
            "[11:30:00] ERROR: Cannot acquire connection: pool exhausted",
            "[11:30:01] INFO: Connection pool size: 50/50 active",
        ],
        "inventory-service": [
            "[11:00:00] INFO: Database query completed",
            "[11:00:00] INFO: Connection released back to pool",
            "[11:30:00] INFO: Operating normally",
        ],
        "database": [
            "[10:00:00] INFO: Active connections: 10",
            "[10:30:00] INFO: Active connections: 25",
            "[11:00:00] WARN: Active connections: 45",
            "[11:30:00] ERROR: Active connections: 50 (max)",
            "[11:30:01] INFO: All connections from order-service IP",
        ],
        "monitoring": [
            "[11:00:00] INFO: Memory usage stable",
            "[11:00:00] INFO: CPU usage normal",
            "[11:30:00] WARN: Connection count trending up over 2 hours",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 40.0, "memory_usage": 55.0, "error_rate": 20.0, "latency_p99": 5000},
        "order-service": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 50.0, "connections_active": 50},
        "inventory-service": {"cpu_usage": 25.0, "memory_usage": 45.0, "error_rate": 0.0, "connections_active": 5},
        "database": {"cpu_usage": 30.0, "memory_usage": 40.0, "connections_active": 50, "threads_active": 50},
        "monitoring": {"cpu_usage": 5.0, "memory_usage": 20.0, "error_rate": 0.0, "latency_p99": 10},
    },
    "ground_truth": {
        "root_cause": "database_connection_timeout",
        "severity": "high",
        "affected_services": ["order-service", "database", "api-gateway"],
        "recommended_action": "restart_service",
    },
}

SCENARIO_RETRY_STORM = {
    "id": "retry_storm",
    "name": "Retry Storm Amplifying Small Failure",
    "difficulty": "hard",
    "alert": {
        "title": "Sudden 10x spike in traffic to payment-service",
        "severity": "critical"
    },
    "services": ["api-gateway", "checkout-service", "payment-service", "order-service", "queue-worker"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Traffic rate: 1000 req/s (normal)",
            "[10:23:50] WARN: Traffic rate: 5000 req/s (elevated)",
            "[10:23:55] ERROR: Traffic rate: 10000 req/s (critical)",
            "[10:24:00] ERROR: Rate limiting activated",
        ],
        "checkout-service": [
            "[10:23:45] INFO: Processing checkout",
            "[10:23:46] WARN: payment-service returned 503, retrying...",
            "[10:23:47] WARN: Retry attempt 2 of 5",
            "[10:23:48] WARN: Retry attempt 3 of 5",
            "[10:23:49] WARN: Retry attempt 4 of 5",
            "[10:23:50] ERROR: All retries failed",
        ],
        "payment-service": [
            "[10:23:44] WARN: External payment gateway slow (2000ms)",
            "[10:23:45] ERROR: Request queue full, rejecting requests",
            "[10:23:46] ERROR: 503 Service Unavailable",
            "[10:23:50] ERROR: Overwhelmed by retry requests",
            "[10:23:55] FATAL: Service crashed due to memory pressure",
        ],
        "order-service": [
            "[10:23:45] INFO: Creating order, waiting for payment",
            "[10:23:50] WARN: Payment timeout, will retry",
            "[10:23:55] WARN: Also retrying payment...",
        ],
        "queue-worker": [
            "[10:23:45] INFO: Processing background jobs normally",
            "[10:23:46] INFO: Job queue size: 100",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 90.0, "memory_usage": 80.0, "error_rate": 60.0, "latency_p99": 10000},
        "checkout-service": {"cpu_usage": 85.0, "memory_usage": 75.0, "error_rate": 90.0, "latency_p99": 30000},
        "payment-service": {"cpu_usage": 100.0, "memory_usage": 95.0, "error_rate": 99.0, "latency_p99": 30000},
        "order-service": {"cpu_usage": 70.0, "memory_usage": 65.0, "error_rate": 80.0, "latency_p99": 25000},
        "queue-worker": {"cpu_usage": 20.0, "memory_usage": 40.0, "error_rate": 0.0, "latency_p99": 100},
    },
    "ground_truth": {
        "root_cause": "network_timeout",
        "severity": "critical",
        "affected_services": ["payment-service", "checkout-service", "order-service", "api-gateway"],
        "recommended_action": "enable_circuit_breaker",
    },
}

SCENARIO_CPU_THROTTLING = {
    "id": "cpu_throttling",
    "name": "CPU Throttling Due to Container Limits",
    "difficulty": "hard",
    "alert": {
        "title": "Inconsistent latency spikes on compute-service",
        "severity": "medium"
    },
    "services": ["api-gateway", "compute-service", "data-service", "scheduler", "metrics-collector"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Request to compute-service (45ms)",
            "[10:23:46] INFO: Request to compute-service (52ms)",
            "[10:23:47] INFO: Request to compute-service (1250ms)",
            "[10:23:48] INFO: Request to compute-service (48ms)",
            "[10:23:49] INFO: Request to compute-service (1340ms)",
        ],
        "compute-service": [
            "[10:23:45] INFO: Processing calculation request",
            "[10:23:46] INFO: Computation completed (40ms)",
            "[10:23:47] INFO: Processing calculation request",
            "[10:23:47] INFO: Computation completed (1200ms)",
            "[10:23:48] DEBUG: Container stats normal",
        ],
        "data-service": [
            "[10:23:45] INFO: Data fetch completed (10ms)",
            "[10:23:46] INFO: Data fetch completed (12ms)",
            "[10:23:47] INFO: Data fetch completed (11ms)",
        ],
        "scheduler": [
            "[10:23:00] INFO: Pod compute-service scheduled on node-3",
            "[10:23:01] INFO: CPU limit: 1000m, Memory limit: 2Gi",
            "[10:23:30] INFO: Node-3 load: 85%",
        ],
        "metrics-collector": [
            "[10:23:45] INFO: compute-service CPU: 95%",
            "[10:23:46] INFO: compute-service CPU: 98%",
            "[10:23:47] WARN: compute-service CPU throttled",
            "[10:23:48] INFO: compute-service CPU: 45%",
            "[10:23:49] WARN: compute-service CPU throttled",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 30.0, "memory_usage": 45.0, "error_rate": 0.0, "latency_p99": 1500},
        "compute-service": {"cpu_usage": 98.0, "memory_usage": 60.0, "error_rate": 0.0, "latency_p99": 1300},
        "data-service": {"cpu_usage": 15.0, "memory_usage": 35.0, "error_rate": 0.0, "latency_p99": 15},
        "scheduler": {"cpu_usage": 10.0, "memory_usage": 25.0, "error_rate": 0.0, "latency_p99": 5},
        "metrics-collector": {"cpu_usage": 8.0, "memory_usage": 20.0, "error_rate": 0.0, "latency_p99": 10},
    },
    "ground_truth": {
        "root_cause": "cpu_throttling",
        "severity": "medium",
        "affected_services": ["compute-service", "api-gateway"],
        "recommended_action": "scale_horizontally",
    },
}

SCENARIO_NETWORK_PARTITION = {
    "id": "network_partition",
    "name": "Network Partition Between Data Centers",
    "difficulty": "hard",
    "alert": {
        "title": "Inconsistent data between primary and replica databases",
        "severity": "critical"
    },
    "services": ["api-gateway", "write-service", "read-service", "database-primary", "database-replica", "network-monitor"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Write request to write-service",
            "[10:23:46] INFO: Read request to read-service",
            "[10:23:47] WARN: Read returned stale data",
            "[10:23:48] INFO: Write request completed",
            "[10:23:49] ERROR: Read-after-write inconsistency detected",
        ],
        "write-service": [
            "[10:23:45] INFO: Writing to primary database",
            "[10:23:46] INFO: Write successful",
            "[10:23:47] INFO: Replication pending...",
            "[10:23:50] WARN: Replication lag: 5000ms",
        ],
        "read-service": [
            "[10:23:46] INFO: Reading from replica",
            "[10:23:46] INFO: Returned cached data",
            "[10:23:47] WARN: Data appears outdated",
        ],
        "database-primary": [
            "[10:23:45] INFO: Write committed",
            "[10:23:46] WARN: Replication stream slow",
            "[10:23:47] ERROR: Cannot reach replica: connection timeout",
            "[10:23:50] ERROR: Replication lag exceeds threshold",
        ],
        "database-replica": [
            "[10:23:45] INFO: Streaming from primary",
            "[10:23:46] WARN: Stream interrupted",
            "[10:23:47] ERROR: Lost connection to primary",
            "[10:23:50] INFO: Serving stale data (last sync: 30s ago)",
        ],
        "network-monitor": [
            "[10:23:40] WARN: Packet loss between DC1 and DC2: 15%",
            "[10:23:45] ERROR: Network partition detected",
            "[10:23:50] WARN: Latency between DCs: 500ms (normal: 10ms)",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 10.0, "latency_p99": 300},
        "write-service": {"cpu_usage": 30.0, "memory_usage": 45.0, "error_rate": 0.0, "latency_p99": 100},
        "read-service": {"cpu_usage": 25.0, "memory_usage": 40.0, "error_rate": 5.0, "latency_p99": 50},
        "database-primary": {"cpu_usage": 40.0, "memory_usage": 60.0, "connections_active": 30, "threads_active": 25},
        "database-replica": {"cpu_usage": 20.0, "memory_usage": 55.0, "connections_active": 40, "threads_active": 15},
        "network-monitor": {"cpu_usage": 10.0, "memory_usage": 20.0, "error_rate": 0.0, "latency_p99": 5},
    },
    "ground_truth": {
        "root_cause": "network_partition",
        "severity": "critical",
        "affected_services": ["database-primary", "database-replica", "write-service", "read-service"],
        "recommended_action": "fix_dns_config",
    },
}

SCENARIO_REDIS_CONNECTION_POOL = {
    "id": "redis_connection_exhausted",
    "name": "Redis Connection Pool Exhausted By Background Jobs",
    "difficulty": "hard",
    "alert": {
        "title": "Session service timing out sporadically",
        "severity": "high"
    },
    "services": ["api-gateway", "session-service", "redis", "analytics-worker", "job-scheduler"],
    "logs": {
        "api-gateway": [
            "[10:23:45] INFO: Request with session validation",
            "[10:23:46] INFO: Session validated (15ms)",
            "[10:23:47] ERROR: Session validation timeout",
            "[10:23:48] INFO: Session validated (12ms)",
            "[10:23:49] ERROR: Session validation timeout",
        ],
        "session-service": [
            "[10:23:45] INFO: Validating session token",
            "[10:23:46] INFO: Redis lookup successful",
            "[10:23:47] ERROR: Cannot get Redis connection: pool exhausted",
            "[10:23:48] INFO: Redis lookup successful",
            "[10:23:49] ERROR: Redis connection timeout after 5s",
        ],
        "redis": [
            "[10:23:40] INFO: Active connections: 95/100",
            "[10:23:45] WARN: Connection pool at 98%",
            "[10:23:47] ERROR: Max connections reached",
            "[10:23:48] INFO: Connection released",
            "[10:23:49] ERROR: Max connections reached",
        ],
        "analytics-worker": [
            "[10:23:00] INFO: Starting hourly analytics job",
            "[10:23:01] INFO: Opening 50 Redis connections for parallel processing",
            "[10:23:30] INFO: Processing 1M events...",
            "[10:23:45] INFO: Still processing, holding connections",
        ],
        "job-scheduler": [
            "[10:23:00] INFO: Triggered analytics-worker job",
            "[10:23:01] INFO: Job running normally",
            "[10:23:30] INFO: No issues detected",
        ],
    },
    "metrics": {
        "api-gateway": {"cpu_usage": 35.0, "memory_usage": 50.0, "error_rate": 15.0, "latency_p99": 5200},
        "session-service": {"cpu_usage": 25.0, "memory_usage": 40.0, "error_rate": 20.0, "latency_p99": 5100},
        "redis": {"cpu_usage": 45.0, "memory_usage": 60.0, "connections_active": 100, "threads_active": 4},
        "analytics-worker": {"cpu_usage": 80.0, "memory_usage": 70.0, "error_rate": 0.0, "connections_active": 50},
        "job-scheduler": {"cpu_usage": 10.0, "memory_usage": 25.0, "error_rate": 0.0, "latency_p99": 10},
    },
    "ground_truth": {
        "root_cause": "redis_connection_pool_exhausted",
        "severity": "high",
        "affected_services": ["analytics-worker", "redis", "session-service", "api-gateway"],
        "recommended_action": "increase_connection_pool_size",
    },
}

ALL_SCENARIOS = [
    SCENARIO_DATABASE_OVERLOAD,
    SCENARIO_SSL_EXPIRED,
    SCENARIO_DISK_FULL,
    SCENARIO_CONFIG_ERROR,
    SCENARIO_NULL_POINTER,
    SCENARIO_BAD_DEPLOYMENT,
    SCENARIO_REDIS_CASCADE,
    SCENARIO_MEMORY_LEAK,
    SCENARIO_DNS_FAILURE,
    SCENARIO_SLOW_QUERY,
    SCENARIO_CACHE_STAMPEDE,
    SCENARIO_DEADLOCK,
    SCENARIO_INTERMITTENT_THREAD_POOL,
    SCENARIO_CONNECTION_LEAK,
    SCENARIO_RETRY_STORM,
    SCENARIO_CPU_THROTTLING,
    SCENARIO_NETWORK_PARTITION,
    SCENARIO_REDIS_CONNECTION_POOL,
]

SCENARIOS_BY_DIFFICULTY = {
    "easy": [s for s in ALL_SCENARIOS if s["difficulty"] == "easy"],
    "medium": [s for s in ALL_SCENARIOS if s["difficulty"] == "medium"],
    "hard": [s for s in ALL_SCENARIOS if s["difficulty"] == "hard"],
}