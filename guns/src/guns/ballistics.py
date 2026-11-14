"""Pure math for hitscan guns (no Endstone imports, so it can be unit-tested)."""
import math
import random

EYE_HEIGHT = 1.62
PASSABLE = {
    "minecraft:air", "minecraft:water", "minecraft:flowing_water",
    "minecraft:short_grass", "minecraft:tallgrass", "minecraft:tall_grass",
    "minecraft:fern", "minecraft:large_fern", "minecraft:vine", "minecraft:snow_layer",
}


def direction_from_angles(yaw_deg: float, pitch_deg: float):
    """Minecraft convention: yaw 0 looks toward +Z, pitch>0 looks down."""
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    return (-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))


def normalize(v):
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / length, v[1] / length, v[2] / length)


def with_spread(direction, spread: float, rng=random):
    if spread <= 0:
        return direction
    return normalize(tuple(c + rng.uniform(-spread, spread) for c in direction))


def ray_sphere(origin, direction, center, radius):
    """Distance along the ray to the first hit of a sphere, or None."""
    ox, oy, oz = (center[i] - origin[i] for i in range(3))
    t_closest = ox * direction[0] + oy * direction[1] + oz * direction[2]
    if t_closest < 0:
        return None
    d2 = ox * ox + oy * oy + oz * oz - t_closest * t_closest
    if d2 > radius * radius:
        return None
    return max(0.0, t_closest - math.sqrt(radius * radius - d2))


def point_at(origin, direction, t):
    return (origin[0] + direction[0] * t, origin[1] + direction[1] * t, origin[2] + direction[2] * t)
