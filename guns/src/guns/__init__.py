import math
import time

from endstone.event import (
    PlayerInteractEvent,
    PlayerItemHeldEvent,
    PlayerQuitEvent,
    event_handler,
)
from endstone.inventory import ItemStack
from endstone.plugin import Plugin

from .ballistics import (
    EYE_HEIGHT,
    PASSABLE,
    direction_from_angles,
    point_at,
    ray_sphere,
    with_spread,
)
from .weapons import WEAPONS, find_by_name

HIT_RADIUS = 0.75  # generous sphere around the middle of a body
SOUND_RADIUS = 48


class GunsPlugin(Plugin):
    api_version = "0.11"
    name = "Guns"
    version = "0.1.0"

    commands = {
        "gun": {
            "description": "Get a gun",
            "usages": ["/gun", "/gun <type: string>"],
            "permissions": ["guns.command.gun"],
        }
    }
    permissions = {
        "guns.command.gun": {"description": "Use /gun", "default": "op"},
    }

    def __init__(self) -> None:
        super().__init__()
        self._auto = {}  # player name -> scheduler task
        self._last_shot = {}  # player name -> monotonic time

    # ---------- command ----------
    def on_command(self, sender, command, args) -> bool:
        if command.name != "gun":
            return False
        if not hasattr(sender, "inventory"):
            sender.send_message("Only players can use /gun")
            return True
        if not args or args[0].lower() not in WEAPONS:
            sender.send_message("Guns: " + ", ".join(WEAPONS))
            return True
        key = args[0].lower()
        gun = WEAPONS[key]
        stack = ItemStack(gun["item"], 1)
        meta = stack.item_meta
        meta.display_name = gun["name"]
        meta.lore = [f"§7{'Auto' if gun['mode'] == 'auto' else 'Semi'}: right click" ]
        stack.set_item_meta(meta)
        sender.inventory.add_item(stack)
        sender.send_message(f"You got: {gun['name']}")
        return True

    # ---------- helpers ----------
    @staticmethod
    def _held_gun(player):
        item = player.inventory.item_in_main_hand
        if item is None or item.type == "minecraft:air":
            return None, None
        meta = item.item_meta
        if meta is None or not meta.has_display_name:
            return None, None
        return find_by_name(meta.display_name)

    def _stop_auto(self, name: str) -> None:
        task = self._auto.pop(name, None)
        if task is not None:
            task.cancel()

    # ---------- events ----------
    @event_handler
    def on_interact(self, event: PlayerInteractEvent) -> None:
        if event.action not in (
            PlayerInteractEvent.Action.RIGHT_CLICK_AIR,
            PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK,
        ):
            return
        player = event.player
        key, gun = self._held_gun(player)
        if gun is None:
            return
        event.cancel()
        name = player.name
        if gun["mode"] == "auto":
            if name in self._auto:
                self._stop_auto(name)
                player.send_popup("§7Auto-fire OFF")
            else:
                player.send_popup("§cAuto-fire ON")
                self._auto[name] = self.server.scheduler.run_task(
                    self, lambda p=player, k=key: self._auto_tick(p, k), delay=0, period=gun["cooldown"]
                )
        else:
            now = time.monotonic()
            if now - self._last_shot.get(name, 0.0) >= gun["cooldown"] / 20.0:
                self._last_shot[name] = now
                self._shoot(player, gun)

    @event_handler
    def on_held(self, event: PlayerItemHeldEvent) -> None:
        self._stop_auto(event.player.name)

    @event_handler
    def on_quit(self, event: PlayerQuitEvent) -> None:
        self._stop_auto(event.player.name)

    def on_disable(self) -> None:
        for name in list(self._auto):
            self._stop_auto(name)

    def _auto_tick(self, player, key) -> None:
        try:
            held_key, gun = self._held_gun(player)
            if not player.is_valid or held_key != key:
                self._stop_auto(player.name)
                return
            self._shoot(player, gun)
        except Exception as exc:
            self._stop_auto(player.name)
            self.logger.error(f"Guns auto-fire stopped: {exc}")

    # ---------- shooting ----------
    def _shoot(self, shooter, gun) -> None:
        loc = shooter.location
        dim = shooter.dimension
        origin = (loc.x, loc.y + EYE_HEIGHT, loc.z)
        base_dir = direction_from_angles(loc.yaw, loc.pitch)
        self._sound(shooter, origin, "firework.blast", 0.7)

        targets = [
            a for a in dim.actors
            if a.runtime_id != shooter.runtime_id and hasattr(a, "health") and a.is_valid and not a.is_dead
        ]
        hits_total = 0
        for _ in range(gun["pellets"]):
            direction = with_spread(base_dir, gun["spread"])
            max_dist = self._wall_distance(dim, origin, direction, gun["range"])
            best, best_t = None, max_dist
            for actor in targets:
                al = actor.location
                center = (al.x, al.y + 0.9, al.z)
                t = ray_sphere(origin, direction, center, HIT_RADIUS)
                if t is not None and t <= best_t:
                    best, best_t = actor, t
            if best is not None:
                best.health = max(0.0, best.health - gun["damage"])
                hits_total += 1
            self._tracer(shooter, origin, direction, best_t)
        if hits_total:
            shooter.send_popup(f"§c● {hits_total}")

    @staticmethod
    def _wall_distance(dim, origin, direction, max_range) -> float:
        t = 0.5
        while t < max_range:
            x, y, z = point_at(origin, direction, t)
            block = dim.get_block_at(math.floor(x), math.floor(y), math.floor(z))
            if block.type not in PASSABLE:
                return t
            t += 0.5
        return float(max_range)

    def _tracer(self, shooter, origin, direction, length) -> None:
        viewers = [p for p in self.server.online_players if p.dimension.name == shooter.dimension.name]
        steps = max(1, min(14, int(length // 3)))
        for i in range(1, steps + 1):
            x, y, z = point_at(origin, direction, i * (length / steps))
            for p in viewers:
                p.spawn_particle("minecraft:basic_smoke_particle", x, y, z)

    def _sound(self, shooter, origin, sound, volume) -> None:
        for p in self.server.online_players:
            if p.dimension.name == shooter.dimension.name:
                pl = p.location
                if (pl.x - origin[0]) ** 2 + (pl.z - origin[2]) ** 2 <= SOUND_RADIUS ** 2:
                    p.play_sound(pl, sound, volume, 1.0)
