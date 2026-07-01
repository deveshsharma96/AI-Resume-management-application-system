import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)
"""
EMAIL_LIMIT = 4
IP_LIMIT = 20
BLOCK_TIME = 2 * 60 * 60      # 2 hours
COUNTER_TTL = 24 * 60 * 60   # 24 hours
"""
EMAIL_LIMIT = 5
IP_LIMIT = 20
BLOCK_TIME = 10 * 60   # 10 minutes (DEV)
COUNTER_TTL = 24 * 60 * 60 

def check_otp_limit(email: str, ip: str, otp_type: str):
    """
    Rate limit OTP requests per:
    - email
    - IP
    - otp_type (login / registration / reset_password / verification)
    """

    email_block_key = f"otp:block:{otp_type}:email:{email}"
    ip_block_key = f"otp:block:{otp_type}:ip:{ip}"

    email_count_key = f"otp:{otp_type}:email:{email}"
    ip_count_key = f"otp:{otp_type}:ip:{ip}"

    # ⛔ Already blocked
    if redis_client.exists(email_block_key):
        ttl = redis_client.ttl(email_block_key)
        return False, f"OTP blocked. Try again after {ttl // 60} minutes."

    if redis_client.exists(ip_block_key):
        ttl = redis_client.ttl(ip_block_key)
        return False, f"Too many OTP attempts from this device. Try again after {ttl // 60} minutes."

    # 🔍 Current counts (before increment)
    email_count = int(redis_client.get(email_count_key) or 0)
    ip_count = int(redis_client.get(ip_count_key) or 0)

    # 🚫 Block if limit reached
    if email_count >= EMAIL_LIMIT:
        redis_client.setex(email_block_key, BLOCK_TIME, "blocked")
        return False, "OTP blocked due to too many requests."

    if ip_count >= IP_LIMIT:
        redis_client.setex(ip_block_key, BLOCK_TIME, "blocked")
        return False, "Too many OTP requests from this device."

    # ✅ Increment counters (OTP WILL BE SENT)
    redis_client.incr(email_count_key)
    redis_client.incr(ip_count_key)

    redis_client.expire(email_count_key, COUNTER_TTL)
    redis_client.expire(ip_count_key, COUNTER_TTL)

    return True, None