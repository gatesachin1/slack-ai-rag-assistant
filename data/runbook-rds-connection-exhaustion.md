# Runbook: RDS Too Many Connections

**Service area:** Amazon RDS (MySQL / PostgreSQL)
**Owner:** Database and Platform SRE teams

## Symptoms
- Application logs show "Too many connections" or connection timeouts.
- CloudWatch metric `DatabaseConnections` is at or near the maximum.
- Latency increases across services that use the database.

## Common causes
1. Connection leak in the application (connections opened but never closed).
2. Pool size too large multiplied by the number of pods after a scale-out.
3. Long-running or blocked queries holding connections.
4. Traffic spike without connection pooling.

## Investigation steps
1. Check `DatabaseConnections`, `CPUUtilization`, and `FreeableMemory` in CloudWatch.
2. List active sessions (for PostgreSQL: `SELECT * FROM pg_stat_activity;`, for MySQL: `SHOW PROCESSLIST;`).
3. Identify the application or user holding the most connections.
4. Look for long-running queries and locks.
5. Check whether a recent scale-out or release changed pool settings.

## Resolution
- Terminate stuck or idle sessions after confirming they are safe to kill.
- Reduce the per-pod connection pool size so total connections stay below the DB limit.
- Introduce **RDS Proxy** to pool and share connections.
- Fix the connection leak in code and release a patch.
- Scale the DB instance class only if the real load requires it.

## Prevention
- Alert at 80% of max connections.
- Set sensible pool sizes and timeouts in every service.
- Use RDS Proxy for bursty or serverless workloads.
