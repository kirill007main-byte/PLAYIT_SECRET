"""Weapon table. Edit the numbers freely.

mode: "semi" = one shot per right click, "auto" = right click toggles continuous fire
item: the vanilla item that is used as the gun (a custom name marks it as a gun)
damage: health points per bullet (a player has 20 = 10 hearts)
cooldown: ticks between shots (20 ticks = 1 second)
pellets: bullets per shot (shotgun)
spread: random aim error
range: maximum distance in blocks
"""

WEAPONS = {
    "pistol": {
        "name": "§ePistol", "item": "minecraft:iron_nugget", "mode": "semi",
        "damage": 5.0, "cooldown": 8, "pellets": 1, "spread": 0.01, "range": 60,
    },
    "smg": {
        "name": "§aSMG", "item": "minecraft:stick", "mode": "auto",
        "damage": 2.0, "cooldown": 3, "pellets": 1, "spread": 0.04, "range": 50,
    },
    "machinegun": {
        "name": "§cMachine Gun", "item": "minecraft:blaze_rod", "mode": "auto",
        "damage": 2.5, "cooldown": 2, "pellets": 1, "spread": 0.06, "range": 70,
    },
    "shotgun": {
        "name": "§6Shotgun", "item": "minecraft:iron_ingot", "mode": "semi",
        "damage": 2.5, "cooldown": 20, "pellets": 8, "spread": 0.08, "range": 25,
    },
    "sniper": {
        "name": "§bSniper", "item": "minecraft:spyglass", "mode": "semi",
        "damage": 18.0, "cooldown": 30, "pellets": 1, "spread": 0.0, "range": 150,
    },
}


def find_by_name(display_name: str):
    for key, gun in WEAPONS.items():
        if gun["name"] == display_name:
            return key, gun
    return None, None
