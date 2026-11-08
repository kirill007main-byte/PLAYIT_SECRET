from pathlib import Path

from endstone.event import PlayerJoinEvent, event_handler
from endstone.inventory import ItemStack
from endstone.plugin import Plugin

from .kit import parse_commands, parse_kit, parse_names

JOIN_DELAY_TICKS = 60  # 3 seconds after joining, so the inventory is ready


class OpJoinPlugin(Plugin):
    """For players listed in ops.txt: grants operator, gives the kit from kit.txt
    and runs startup-commands.txt. Needed because behind a proxy the server gets no XUID."""

    api_version = "0.11"
    name = "OpJoin"
    version = "0.2.0"

    def __init__(self) -> None:
        super().__init__()
        self._served: set[str] = set()  # kit is given once per player per server run

    def _read(self, filename: str) -> str:
        for base in (Path("."), Path("bedrock_server")):
            path = base / filename
            if path.exists():
                return path.read_text(encoding="utf-8")
        return ""

    def on_enable(self) -> None:
        self.register_events(self)
        ops = parse_names(self._read("ops.txt"))
        kit, errors = parse_kit(self._read("kit.txt"))
        self.logger.info(f"OpJoin enabled: {len(ops)} operator name(s), {len(kit)} kit line(s)")
        for err in errors:
            self.logger.warning(f"kit.txt {err}")

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        player = event.player
        key = player.name.lower()
        if key not in parse_names(self._read("ops.txt")):
            return
        player.is_op = True
        self.logger.info(f"Granted operator to {player.name}")
        if key in self._served:
            return
        self._served.add(key)
        self.server.scheduler.run_task(self, lambda: self._give(player), delay=JOIN_DELAY_TICKS)

    def _give(self, player) -> None:
        try:
            self._run_commands(player)
            self._give_kit(player)
        except Exception as exc:  # never break the join because of the kit
            self.logger.error(f"OpJoin kit failed for {player.name}: {exc}")

    def _run_commands(self, player) -> None:
        commands, refused = parse_commands(self._read("startup-commands.txt"), player.name)
        for line in refused:
            self.logger.warning(f"startup-commands.txt: '{line}' refused (op is granted via ops.txt)")
        for command in commands:
            ok = self.server.dispatch_command(self.server.command_sender, command)
            self.logger.info(f"command '{command}' -> {'ok' if ok else 'failed'}")

    def _make_stack(self, entry, amount: int) -> ItemStack:
        stack = ItemStack(entry["item"], amount, entry["data"])
        if entry["enchants"]:
            meta = stack.item_meta
            for ench, level in entry["enchants"]:
                if not meta.add_enchant(ench, level, True):
                    self.logger.warning(f"could not add {ench} {level} to {entry['item']}")
            stack.set_item_meta(meta)
        return stack

    def _give_kit(self, player) -> None:
        entries, _ = parse_kit(self._read("kit.txt"))
        inv = player.inventory
        for entry in entries:
            try:
                slot = entry["slot"]
                if slot in ("helmet", "chestplate", "leggings", "boots", "offhand"):
                    stack = self._make_stack(entry, 1)
                    if slot == "offhand":
                        inv.item_in_off_hand = stack
                    else:
                        setattr(inv, slot, stack)
                    continue
                remaining = entry["amount"]
                while remaining > 0:  # respect max stack size (totems stack to 1)
                    probe = self._make_stack(entry, 1)
                    size = max(1, min(remaining, probe.max_stack_size))
                    leftover = inv.add_item(self._make_stack(entry, size))
                    if leftover:
                        self.logger.warning(f"inventory full, {entry['item']} not fully given")
                        break
                    remaining -= size
            except Exception as exc:
                self.logger.error(f"kit item {entry['item']} failed: {exc}")
        self.logger.info(f"Kit given to {player.name}")
