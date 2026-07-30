import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_loyalty_level(points: int) -> str:
    if points >= 7000:
        return "Platinum"
    elif points >= 3000:
        return "Gold"
    elif points >= 1000:
        return "Silver"
    return "Bronze"


def calculate_reward_points(amount: float) -> int:
    return int(amount / 10)


def format_currency(amount: float) -> str:
    return f"₹{amount:,.2f}"


def get_status_color(status: str) -> str:
    colors = {
        "pending":    "🟡",
        "accepted":   "🟢",
        "rejected":   "🔴",
        "processing": "🔵",
        "shipped":    "🟣",
        "delivered":  "✅",
        "cancelled":  "⛔",
    }
    return colors.get(status, "⚪")


def level_badge(level: str) -> str:
    badges = {
        "Bronze":   "🥉 Bronze",
        "Silver":   "🥈 Silver",
        "Gold":     "🥇 Gold",
        "Platinum": "💎 Platinum",
    }
    return badges.get(level, level)
