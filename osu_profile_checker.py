import os
import sys
from collections import Counter
from datetime import datetime

import requests
import tkinter as tk
from tkinter import messagebox

API_URL_USER = "https://osu.ppy.sh/api/get_user"
API_URL_USER_BEST = "https://osu.ppy.sh/api/get_user_best"
API_URL_BEATMAPS = "https://osu.ppy.sh/api/get_beatmaps"


def get_osu_user(username: str) -> dict:
    """Fetch osu! user data from the public API."""
    api_key = os.getenv("OSU_API_KEY")
    if not api_key:
        raise RuntimeError("OSU_API_KEY environment variable not set")
    params = {"k": api_key, "u": username}
    response = requests.get(API_URL_USER, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError("User not found")
    return data[0]


def get_user_best(username: str, limit: int = 50) -> list[dict]:
    """Return the user's best scores."""
    api_key = os.getenv("OSU_API_KEY")
    if not api_key:
        raise RuntimeError("OSU_API_KEY environment variable not set")
    params = {"k": api_key, "u": username, "limit": str(limit)}
    response = requests.get(API_URL_USER_BEST, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_beatmap_creator(beatmap_id: str, cache: dict[str, str]) -> str:
    """Fetch the creator of a beatmap using a small cache."""
    if beatmap_id in cache:
        return cache[beatmap_id]
    api_key = os.getenv("OSU_API_KEY")
    if not api_key:
        raise RuntimeError("OSU_API_KEY environment variable not set")
    params = {"k": api_key, "b": beatmap_id}
    response = requests.get(API_URL_BEATMAPS, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    creator = data[0]["creator"] if data else "Unknown"
    cache[beatmap_id] = creator
    return creator


def get_beatmap_stats(beatmap_id: str, cache: dict[str, dict]) -> dict:
    """Return star rating and other info for a beatmap."""
    if beatmap_id in cache:
        return cache[beatmap_id]
    api_key = os.getenv("OSU_API_KEY")
    if not api_key:
        raise RuntimeError("OSU_API_KEY environment variable not set")
    params = {"k": api_key, "b": beatmap_id}
    response = requests.get(API_URL_BEATMAPS, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not data:
        stats = {"sr": 0.0, "ar": 0.0, "od": 0.0}
    else:
        beatmap = data[0]
        stats = {
            "sr": float(beatmap.get("difficultyrating", 0)),
            "ar": float(beatmap.get("diff_approach", 0)),
            "od": float(beatmap.get("diff_overall", 0)),
        }
    cache[beatmap_id] = stats
    return stats


MOD_BITS = {
    0: "NoMod",
    1: "NF",
    2: "EZ",
    4: "TD",
    8: "HD",
    16: "HR",
    32: "SD",
    64: "DT",
    128: "RX",
    256: "HT",
    512: "NC",
    1024: "FL",
    4096: "SO",
}


def parse_mods(bitmask: int) -> list[str]:
    """Decode the mods bitmask into a list of mod abbreviations."""
    if bitmask == 0:
        return ["NoMod"]
    mods: list[str] = []
    for bit, name in MOD_BITS.items():
        if bit != 0 and bitmask & bit:
            mods.append(name)
    return mods


def score_accuracy(score: dict) -> float:
    """Calculate accuracy for a single score."""
    try:
        n50 = int(score.get("count50", 0))
        n100 = int(score.get("count100", 0))
        n300 = int(score.get("count300", 0))
        miss = int(score.get("countmiss", 0))
    except (TypeError, ValueError):
        return 0.0
    total = n50 + n100 + n300 + miss
    if total == 0:
        return 0.0
    return (50 * n50 + 100 * n100 + 300 * n300) / (300 * total) * 100


def analyze_best_scores(best_scores: list[dict]) -> dict:
    """Return aggregated statistics from the player's best plays."""
    cache: dict[str, dict] = {}
    mod_counter: Counter = Counter()
    total_sr = total_ar = total_od = total_acc = 0.0
    for score in best_scores:
        beatmap_id = score.get("beatmap_id")
        if beatmap_id:
            stats = get_beatmap_stats(beatmap_id, cache)
            total_sr += stats["sr"]
            total_ar += stats["ar"]
            total_od += stats["od"]
        total_acc += score_accuracy(score)
        mods = parse_mods(int(score.get("enabled_mods", 0)))
        mod_counter.update(mods)
    n = len(best_scores)
    return {
        "average_sr": total_sr / n if n else 0.0,
        "average_ar": total_ar / n if n else 0.0,
        "average_od": total_od / n if n else 0.0,
        "average_accuracy": total_acc / n if n else 0.0,
        "most_used_mod": mod_counter.most_common(1)[0][0] if mod_counter else "Unknown",
    }


def find_favorite_mapper(best_scores: list[dict]) -> str:
    """Determine the mapper that appears most often in the user's best plays."""
    cache: dict[str, str] = {}
    creators: list[str] = []
    for score in best_scores:
        beatmap_id = score.get("beatmap_id")
        if beatmap_id:
            creators.append(get_beatmap_creator(beatmap_id, cache))
    if not creators:
        return "Unknown"
    return Counter(creators).most_common(1)[0][0]


def compute_improvement_rate(user: dict) -> float:
    """Estimate improvement rate as PP gained per day since account creation."""
    join = datetime.strptime(user["join_date"], "%Y-%m-%d %H:%M:%S")
    days = max((datetime.utcnow() - join).days, 1)
    pp = float(user.get("pp_raw", 0))
    return pp / days


def analyze_strengths(user: dict) -> list[str]:
    """Generate a short list of the player's strengths."""
    strengths: list[str] = []
    accuracy = float(user.get("accuracy", 0))
    level = float(user.get("level", 0))
    playcount = int(user.get("playcount", 0))
    pp = float(user.get("pp_raw", 0))
    if accuracy >= 98:
        strengths.append("great accuracy")
    elif accuracy >= 95:
        strengths.append("good accuracy")
    if pp >= 5000:
        strengths.append("high pp")
    if level >= 100:
        strengths.append("very high level")
    if playcount >= 10000:
        strengths.append("lots of experience")
    return strengths


def format_user_profile(
    user: dict,
    improvement: float,
    strengths: list[str],
    favorite_mapper: str,
    best_analysis: dict,
) -> str:
    """Return formatted profile information."""
    lines = [
        f"Username: {user.get('username')}",
        f"Performance Points: {user.get('pp_raw')}",
        f"Play count: {user.get('playcount')}",
        f"Level: {user.get('level')}",
        f"Ranked score: {user.get('ranked_score')}",
        f"Improvement rate: {improvement:.2f} pp/day",
        f"Favourite mapper: {favorite_mapper}",
        f"Average star rating: {best_analysis['average_sr']:.2f}",
        f"Avg AR/OD: {best_analysis['average_ar']:.1f}/{best_analysis['average_od']:.1f}",
        f"Average accuracy on best plays: {best_analysis['average_accuracy']:.2f}%",
        f"Most used mod: {best_analysis['most_used_mod']}",
    ]
    if strengths:
        lines.append("Stärken:")
        lines.extend(f"- {s}" for s in strengths)
    return "\n".join(lines)


def print_user_profile(
    user: dict,
    improvement: float,
    strengths: list[str],
    favorite_mapper: str,
    best_analysis: dict,
) -> None:
    """Pretty print the profile information and analysis."""
    print(format_user_profile(user, improvement, strengths, favorite_mapper, best_analysis))


def run_analysis(username: str) -> str:
    """Fetch data and return formatted profile information."""
    user = get_osu_user(username)
    best_scores = get_user_best(username)
    favorite = find_favorite_mapper(best_scores)
    improvement = compute_improvement_rate(user)
    strengths = analyze_strengths(user)
    best_analysis = analyze_best_scores(best_scores)
    return format_user_profile(user, improvement, strengths, favorite, best_analysis)


def run_gui() -> None:
    """Start a simple GUI to prompt for a username and display results."""

    def on_ok() -> None:
        username = entry.get().strip()
        if not username:
            messagebox.showwarning("Fehler", "Bitte einen Nutzernamen eingeben.")
            return
        try:
            info = run_analysis(username)
        except ValueError:
            messagebox.showinfo("Nicht gefunden", f"User '{username}' nicht gefunden.")
            return
        messagebox.showinfo("osu! Profil", info)

    root = tk.Tk()
    root.title("osu! Profile Checker")
    tk.Label(root, text="Benutzername:").pack(padx=10, pady=(10, 0))
    entry = tk.Entry(root)
    entry.pack(padx=10, pady=5)
    tk.Button(root, text="OK", command=on_ok).pack(pady=(0, 10))
    root.mainloop()


def main(argv: list[str]) -> None:
    if len(argv) == 2:
        username = argv[1]
        try:
            info = run_analysis(username)
        except ValueError:
            print(f"User '{username}' nicht gefunden.")
            sys.exit(1)
        print(info)
    else:
        run_gui()


if __name__ == "__main__":
    main(sys.argv)

