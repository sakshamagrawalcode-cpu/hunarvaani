import logging
import time

import psycopg
import redis

from core.config import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s worker %(message)s")
log = logging.getLogger("worker")


def main() -> None:
    settings = load_settings()
    log.info("started; callbacks queue is not consumed yet (Step 7)")
    while True:
        try:
            with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
                conn.execute("SELECT 1")
            redis.Redis.from_url(settings.redis_url, socket_connect_timeout=3).ping()
            log.info("heartbeat: db and redis reachable")
        except Exception as exc:
            log.warning("heartbeat: dependency unreachable (%s)", type(exc).__name__)
        time.sleep(30)


if __name__ == "__main__":
    main()
