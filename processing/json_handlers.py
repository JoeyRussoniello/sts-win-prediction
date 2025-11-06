"""A module for handling the conversion from nested JSON data to a clean tabular dataset"""

# Rich Progress Bar for Nice Loading Display
import json
import os
from copy import deepcopy

import pandas as pd
from rich.console import Console

console = Console()


def process_run(run: dict) -> list[dict]:
    """Flatten a Slay the Spire run into floor-level state records, including running deck state."""
    local_run = run["event"]
    run_id = local_run["seed_source_timestamp"]

    floors = init_floors(local_run, run_id)
    add_base_stats(local_run, floors)
    add_pathing(local_run, floors)
    add_card_choices(local_run, floors)
    add_relics(local_run, floors)
    add_events(local_run, floors)
    add_campfires(local_run, floors)
    add_purchases(local_run, floors)
    add_damage(local_run, floors)
    add_deck_state(local_run, floors)
    add_relic_state(local_run, floors)

    return floors


# ---------------------------------------------------------------------------
# Safe floor accessor
# ---------------------------------------------------------------------------
def safe_get_floor(d: dict):
    """Safely extract a floor index. Returns None if missing, else int."""
    f = d.get("floor")
    if f is None:
        return None
    return int(f)


# ---------------------------------------------------------------------------
# Floor-level helpers
# ---------------------------------------------------------------------------
def init_floors(run: dict, run_id: int) -> list[dict]:
    """Basic Initialization of Row Structure and Shared Run Characteristics/Labels"""
    n_floors = run.get("floor_reached", 0)
    victory = run.get("victory", False)
    character = run.get("character_chosen", None)
    asc_level = run.get("ascension_level", None)
    is_asc = run.get("is_ascension", False)
    win_rate = run.get("win_rate", None)

    return [
        {
            "run_id": run_id,
            "floor": f,
            "victory": victory,
            "character": character,
            "asc_level": asc_level,
            "is_ascension": is_asc,
            "win_rate": win_rate,
        }
        for f in range(n_floors + 1)
    ]


def add_base_stats(run: dict, floors: list[dict]):
    for i, (max_hp, cur_hp, gold) in enumerate(
        zip(
            run.get("max_hp_per_floor", []),
            run.get("current_hp_per_floor", []),
            run.get("gold_per_floor", []),
        )
    ):
        if i < len(floors):
            floors[i]["max_hp"] = max_hp
            floors[i]["cur_hp"] = cur_hp
            floors[i]["gold"] = gold


def add_pathing(run: dict, floors: list[dict]):
    """Align path symbols with correct floor indices."""
    path = run.get("path_per_floor", [])
    n = len(floors)

    for f in range(n):
        if f == 0:
            floors[f]["path_symbol"] = None
            floors[f]["next_path_symbol"] = path[0] if len(path) > 0 else None
        else:
            idx = f - 1
            floors[f]["path_symbol"] = path[idx] if idx < len(path) else None
            floors[f]["next_path_symbol"] = (
                path[idx + 1] if (idx + 1) < len(path) else None
            )


def add_card_choices(run: dict, floors: list[dict]):
    for choice in run.get("card_choices", []):
        f = safe_get_floor(choice)
        if f is None or f >= len(floors):
            return
        floors[f]["card_picked"] = choice.get("picked")
        for j, np in enumerate(choice.get("not_picked", [])):
            floors[f][f"not_picked_{j + 1}"] = np


def add_relics(run: dict, floors: list[dict]):
    for relic in run.get("relics_obtained", []):
        f = safe_get_floor(relic)
        if f is None or f >= len(floors):
            return
        floors[f]["relic_obtained"] = relic.get("key")


def add_events(run: dict, floors: list[dict]):
    for ev in run.get("event_choices", []):
        f = safe_get_floor(ev)
        if f is None or f >= len(floors):
            return
        floors[f]["event_name"] = ev.get("event_name")
        floors[f]["event_choice"] = ev.get("player_choice")
        floors[f]["event_cards_obtained"] = ev.get("cards_obtained", [])
        floors[f]["event_relics_obtained"] = ev.get("relics_obtained", [])


def add_campfires(run: dict, floors: list[dict]):
    for camp in run.get("campfire_choices", []):
        f = safe_get_floor(camp)
        if f is None or f >= len(floors):
            return
        floors[f]["campfire_action"] = camp.get("key")
        floors[f]["campfire_target"] = camp.get("data")


def add_purchases(run: dict, floors: list[dict]):
    for item, f in zip(
        run.get("items_purchased", []), run.get("item_purchase_floors", [])
    ):
        if f < len(floors):
            floors[f].setdefault("items_purchased", []).append(item)
    for f in floors:
        if "items_purchased" in f:
            f["items_purchased"] = ",".join(f["items_purchased"])


def add_damage(run: dict, floors: list[dict]):
    for d in run.get("damage_taken", []):
        f = safe_get_floor(d)
        if f is None or f >= len(floors):
            return
        floors[f]["combat_enemies"] = d.get("enemies")
        floors[f]["combat_damage"] = d.get("damage", 0)
        floors[f]["combat_turns"] = d.get("turns", 0)


def add_deck_state(run: dict, floors: list[dict]):
    """Build a per-floor running deck list"""
    deck = deepcopy(get_starting_deck(run))
    purges = run.get("items_purged", [])
    purchase_floors = run.get("item_purchase_floors", [])
    campfires = run.get("campfire_choices", [])
    card_choices = run.get("card_choices", [])
    event_choices = run.get("event_choices", [])

    for i, floor in enumerate(floors):
        for c in card_choices:
            f = safe_get_floor(c)
            if f is None:
                return
            if f == i and c.get("picked") != "SKIP":
                deck.append(c["picked"])

        for ev in event_choices:
            f = safe_get_floor(ev)
            if f is None:
                return
            if f == i and ev.get("cards_obtained"):
                for card in ev["cards_obtained"]:
                    deck.append(card)

        for purge, pf in zip(purges, purchase_floors):
            if pf == i and purge in deck:
                deck.remove(purge)

        for camp in [
            c for c in campfires if safe_get_floor(c) == i and c["key"] == "SMITH"
        ]:
            target = camp.get("data")
            if target and target in deck:
                deck.remove(target)
                deck.append(f"{target}+1")

        floor["deck"] = deepcopy(deck)
        floor["deck_size"] = len(deck)


def add_relic_state(run: dict, floors: list[dict]):
    relics = []
    start_relics = run.get("relics", [])
    if start_relics:
        relics.append(start_relics[0])

    for r in run.get("relics_obtained", []):
        f = safe_get_floor(r)
        if f is None:
            return
        if f == 0 and r.get("key") not in relics:
            relics.append(r["key"])

    event_choices = run.get("event_choices", [])
    relic_events = run.get("relics_obtained", [])
    boss_relics = run.get("boss_relics", [])
    boss_floors = [
        i for i, f in enumerate(floors) if f.get("path_symbol") in ("B", "BOSS")
    ]
    boss_relic_index = 0

    for f in range(len(floors)):
        for r in relic_events:
            rf = safe_get_floor(r)
            if rf is None:
                return
            if rf == f and r["key"] not in relics:
                relics.append(r["key"])

        for ev in event_choices:
            ef = safe_get_floor(ev)
            if ef is None:
                return
            if ef == f and ev.get("relics_obtained"):
                for rk in ev["relics_obtained"]:
                    if rk not in relics:
                        relics.append(rk)

        if f in boss_floors and boss_relic_index < len(boss_relics):
            picked = boss_relics[boss_relic_index].get("picked")
            if picked and picked not in relics:
                relics.append(picked)
            boss_relic_index += 1

        floors[f]["relics"] = relics.copy()
        floors[f]["num_relics"] = len(relics)


def get_starting_deck(run: dict) -> list[str]:
    """Infer the starting deck based on character and initial data."""
    char = run.get("character_chosen", "")
    if char == "IRONCLAD":
        return ["Strike_R"] * 5 + ["Defend_R"] * 4 + ["Bash"]
    elif char == "THE_SILENT":
        return ["Strike_G"] * 5 + ["Defend_G"] * 5 + ["Survivor", "Neutralize"]
    elif char == "DEFECT":
        return ["Strike_B"] * 4 + ["Defend_B"] * 4 + ["Zap", "Dualcast"]
    elif char == "WATCHER":
        return ["Strike_P"] * 4 + ["Defend_P"] * 4 + ["Eruption", "Vigilance"]
    raise KeyError(f"Invalid Character Chose {char}")


# MAIN FUNCTION
def load_all_runs(data: list[dict], increment: int) -> list[dict]:
    """
    Process a list of Slay the Spire run JSONs with a progress bar.

    Parameters
    ----------
    data : list[dict]
        A list of runs loaded from the game logs.

    Returns
    -------
    all_rows : list[dict]
        A flattened list of floor-level records from all runs.
    increment: int
        Log the results every `increment` runs processed
    """
    all_rows = []
    total_runs = len(data)
    console.print(f"[bold cyan]Starting to process {total_runs} runs...[/bold cyan]")

    for i, run in enumerate(data):
        try:
            rows = process_run(run)
            if rows:
                all_rows.extend(rows)
        except Exception as e:
            console.print(f"[red]Run {i} failed:[/red] {e}")
        finally:
            if i % increment == 0:
                console.print(f"[deep_sky_blue4]Processed run {i}")

    console.print(
        f"\n[bold green]✅ Finished processing {len(all_rows)} floor records "
        f"from {total_runs} runs.[/bold green]"
    )
    return all_rows


if __name__ == "__main__":
    cur_path = os.path.dirname(__file__)
    repo_path = os.path.dirname(cur_path)
    # Cross-OS safe way of accessing data
    data_path = os.path.join(repo_path, "data", "sample.json")
    output_path = os.path.join(repo_path, "data", "processed_sample.csv")
    # * NOT RESISTANT TO REPO STRUCTURE CHANGE
    console.print(
        "====================================================================="
    )
    console.print("[bold gray]Beginning JSON file load.")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    console.print("[white]JSON data loaded")
    all_rows = load_all_runs(data, increment=10_000)

    df = pd.DataFrame(all_rows)
    # Overwrite the current CSV
    console.print("[green]Data loaded to pandas dataframe")
    df.to_csv(output_path, index=False, mode="w")
    console.print(f"[green]Data written to {output_path}")
