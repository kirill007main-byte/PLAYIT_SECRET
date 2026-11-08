"""Parsing helpers for kit.txt and startup-commands.txt (no Endstone imports, easy to test)."""

SLOTS = {"helmet", "chestplate", "leggings", "boots", "offhand", "give"}


def parse_names(text: str) -> set[str]:
    names = set()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line.lower())
    return names


def parse_kit(text: str):
    """Each line: <slot> <item> [amount] [enchant:level ...] [data=N]

    slot: helmet | chestplate | leggings | boots | offhand | give
    Returns (entries, errors); entry = dict(slot, item, amount, data, enchants[(id, level)]).
    """
    entries, errors = [], []
    for num, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2 or parts[0].lower() not in SLOTS:
            errors.append(f"line {num}: expected '<slot> <item> ...', got: {line}")
            continue
        slot, item, rest = parts[0].lower(), parts[1], parts[2:]
        if ":" not in item:
            item = "minecraft:" + item
        amount, data, enchants = 1, 0, []
        for tok in rest:
            if tok.isdigit():
                amount = int(tok)
            elif tok.lower().startswith("data="):
                try:
                    data = int(tok.split("=", 1)[1])
                except ValueError:
                    errors.append(f"line {num}: bad data value '{tok}'")
            elif ":" in tok:
                name, _, level = tok.rpartition(":")
                if not level.isdigit() or not name:
                    errors.append(f"line {num}: bad enchantment '{tok}'")
                    continue
                if ":" not in name:
                    name = "minecraft:" + name
                enchants.append((name, int(level)))
            else:
                errors.append(f"line {num}: unknown token '{tok}'")
        entries.append(
            {"slot": slot, "item": item, "amount": max(1, amount), "data": data, "enchants": enchants}
        )
    return entries, errors


def parse_commands(text: str, player: str):
    """Commands run when a listed player joins. {player} is replaced by the name.
    op/deop lines are refused (behind a proxy the XUID is empty, so /op could match everyone)."""
    commands, refused = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.lstrip("/").strip()
        head = line.split(None, 1)[0].lower()
        if head in ("op", "deop"):
            refused.append(line)
            continue
        commands.append(line.replace("{player}", player))
    return commands, refused
