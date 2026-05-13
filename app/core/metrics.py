from app.core.redis_client import redis_client

def increment_request_count():
    if redis_client:
        try:
            redis_client.incr("metrics:request_count")
        except Exception:
            pass

def increment_error_count():
    if redis_client:
        try:
            redis_client.incr("metrics:error_count")
        except Exception:
            pass

def add_response_time(t: float):
    if redis_client:
        try:
            redis_client.incrbyfloat("metrics:total_response_time", t)
        except Exception:
            pass

def add_recent_log(entry: str):
    if redis_client:
        try:
            redis_client.lpush("metrics:recent_logs", entry)
            redis_client.ltrim("metrics:recent_logs", 0, 9)  # keep last 10
        except Exception:
            pass

def get_metrics():
    if not redis_client:
        return {"request_count": 0, "error_count": 0, "total_response_time": 0.0, "recent_logs": []}
    try:
        request_count = int(redis_client.get("metrics:request_count") or 0)
        error_count = int(redis_client.get("metrics:error_count") or 0)
        total_response_time = float(redis_client.get("metrics:total_response_time") or 0.0)
        recent_logs = redis_client.lrange("metrics:recent_logs", 0, 9)
        return {
            "request_count": request_count,
            "error_count": error_count,
            "total_response_time": total_response_time,
            "recent_logs": recent_logs
        }
    except Exception:
        return {"request_count": 0, "error_count": 0, "total_response_time": 0.0, "recent_logs": []}