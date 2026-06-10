import math
import statistics
from typing import List, Tuple

def rasch_probability(theta: float, b: float) -> float:
    return math.exp(theta - b) / (1 + math.exp(theta - b))

def update_theta(theta: float, answers: List[Tuple[bool, float]], iterations: int = 10) -> float:
    current_theta = theta
    for _ in range(iterations):
        numerator = 0.0
        denominator = 0.0
        for is_correct, b in answers:
            p = rasch_probability(current_theta, b)
            q = 1 - p
            numerator += (1 if is_correct else 0) - p
            denominator += p * q
        if denominator == 0:
            break
        current_theta += numerator / denominator
        current_theta = max(-4.0, min(4.0, current_theta))
    return round(current_theta, 3)

def calculate_z_score(theta: float, all_thetas: List[float]) -> float:
    """Rasmiy formula: Z = (θ - μ) / σ"""
    if len(all_thetas) < 2:
        return 0.0
    mu = statistics.mean(all_thetas)
    sigma = statistics.stdev(all_thetas)
    if sigma == 0:
        return 0.0
    return round((theta - mu) / sigma, 3)

def calculate_t_score(z: float) -> float:
    """Rasmiy formula: T = 50 + 10Z"""
    return round(50 + 10 * z, 2)

def t_score_to_grade(t: float) -> str:
    if t >= 70:
        return "🏆 A+"
    elif t >= 65:
        return "⭐⭐⭐ A"
    elif t >= 60:
        return "⭐⭐ B+"
    elif t >= 55:
        return "⭐ B"
    elif t >= 50:
        return "🔵 C+"
    elif t >= 46:
        return "🟡 C"
    else:
        return "🔴 C dan quyi"

def tabaqalashtirilgan_ball(raw_ball: float, max_ball: float, min_chegara: float = 65) -> float:
    """Ball * max_ball / min_chegara"""
    result = raw_ball * max_ball / min_chegara
    return round(min(result, max_ball), 2)

def get_full_result(theta: float, all_thetas: List[float]) -> dict:
    z = calculate_z_score(theta, all_thetas)
    t = calculate_t_score(z)
    grade = t_score_to_grade(t)
    return {"theta": theta, "z_score": z, "t_score": t, "grade": grade}

def theta_to_level(theta: float) -> str:
    if theta >= 2.0:
        return "🏆 A+"
    elif theta >= 1.0:
        return "⭐⭐⭐ A"
    elif theta >= 0.0:
        return "⭐⭐ B+"
    elif theta >= -1.0:
        return "⭐ B"
    else:
        return "🔴 C"

def get_wright_map_text(users_theta: List[float], questions_b: List[Tuple[str, float]]) -> str:
    lines = ["📊 WRIGHT MAP\n", "Logit | Qobiliyat  |  Savollar\n", "-" * 40]
    for logit in range(4, -5, -1):
        u_count = sum(1 for t in users_theta if logit - 0.5 <= t < logit + 0.5)
        q_names = [name for name, b in questions_b if logit - 0.5 <= b < logit + 0.5]
        u_str = "●" * u_count if u_count > 0 else " "
        q_str = ", ".join(q_names[:2]) if q_names else " "
        lines.append(f"  {logit:+d}  | {u_str:<10} | {q_str}")
    return "\n".join(lines)
