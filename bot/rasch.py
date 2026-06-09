import math
from typing import List, Tuple

def rasch_probability(theta: float, b: float) -> float:
    """
    Rasch modeli ehtimollik formulasi:
    P(correct) = exp(theta - b) / (1 + exp(theta - b))
    theta = qobiliyat darajasi
    b = savol qiyinlik darajasi
    """
    return math.exp(theta - b) / (1 + math.exp(theta - b))

def update_theta(theta: float, answers: List[Tuple[bool, float]], iterations: int = 10) -> float:
    """
    MLE (Maximum Likelihood Estimation) bilan theta yangilash
    answers = [(is_correct, difficulty), ...]
    """
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
        # Chegara: -4 dan +4 gacha
        current_theta = max(-4.0, min(4.0, current_theta))
    return round(current_theta, 3)

def theta_to_level(theta: float) -> str:
    """Theta qiymatini darajaga aylantirish"""
    if theta >= 2.0:
        return "🏆 Ekspert"
    elif theta >= 1.0:
        return "⭐⭐⭐ Yuqori"
    elif theta >= 0.0:
        return "⭐⭐ O'rta-yuqori"
    elif theta >= -1.0:
        return "⭐ O'rta"
    else:
        return "📚 Boshlang'ich"

def calculate_infit(answers: List[Tuple[bool, float, float]]) -> float:
    """
    Infit statistikasi (ichki moslik)
    answers = [(is_correct, difficulty, theta), ...]
    """
    numerator = 0.0
    denominator = 0.0
    for is_correct, b, theta in answers:
        p = rasch_probability(theta, b)
        q = 1 - p
        w = p * q
        residual = (1 if is_correct else 0) - p
        numerator += w * (residual ** 2) / w
        denominator += w
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 3)

def get_wright_map_text(users_theta: List[float], questions_b: List[Tuple[str, float]]) -> str:
    """
    Wright Map matnli ko'rinishi
    """
    lines = ["📊 WRIGHT MAP\n", "Logit | Qobiliyat  |  Savollar\n", "-" * 40]
    for logit in range(4, -5, -1):
        u_count = sum(1 for t in users_theta if logit - 0.5 <= t < logit + 0.5)
        q_names = [name for name, b in questions_b if logit - 0.5 <= b < logit + 0.5]
        u_str = "●" * u_count if u_count > 0 else " "
        q_str = ", ".join(q_names[:2]) if q_names else " "
        lines.append(f"  {logit:+d}  | {u_str:<10} | {q_str}")
    return "\n".join(lines)
