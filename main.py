import bisect
import builtins
import math
import os
from pathlib import Path
import collision
from pytiled_parser import parse_map
import random
import sys
from typing import Optional
import wasabi2d.loop
from wasabi2d.clock import Clock
import wasabi2d as w2d
import wasabigeom
from wasabigeom import vec2

# import after wasabi2d, this suppresses the PyGame stdout message
import pygame

vec2_zero = vec2(0, 0)

TILE_SIZE: int = 18
FRICTION: float = 0.1
GRAVITY: float = 20
TILE_DIMS: vec2 = vec2(TILE_SIZE, TILE_SIZE)

game = None
level: Optional['Level'] = None
player = None

gamedir_path = Path(sys.argv[0]).resolve().parent

colors = {'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'gray'}

layers = list(range(17))
background_layer, red_layer, red_off_layer, orange_layer, orange_off_layer, yellow_layer, orange_off_layer, green_layer, green_off_layer, blue_layer, blue_off_layer, purple_layer, purple_off_layer, gray_layer, sprite_layer, player_layer, hud_layer, = layers

color_to_layer = {
    'red': red_layer,
    'orange': orange_layer,
    'yellow': yellow_layer,
    'green': green_layer,
    'blue': blue_layer,
    'purple': purple_layer,
    'gray': gray_layer,
}
color_to_rgb = {
    'red': (1, 0, 0),
    'orange': (1, 0.4, 0),
    'yellow': (1, 0.9, 0),
    'green': (0, 0.8, 0.1),
    'blue': (0, 0.3, 0.9),
    'purple': (0.8, 0, 1.0),
    'gray': (0.6, 0.6, 0.6),
}

scene_width = 900
scene_height = 540

scene_camera_bounding_box = None

scene = w2d.Scene(
    width=scene_width,
    height=scene_height,
    ##scaler='nearest'
    title="The Red Planet",
)
scene.background = (0.9, 0.9, 0.9)

LIGHT_LAYER = 1000
lights = scene.layers[LIGHT_LAYER]
scene.chain = [
    w2d.chain.Light(
        light=w2d.chain.Layers([LIGHT_LAYER]),
        diffuse=w2d.chain.LayerRange(stop=LIGHT_LAYER - 1),
        ambient=(0.6, 0.3, 0.2, 1.0),
    )
]

color_tile_maps = {}
color_off_tile_maps = {}

for color, layer in color_to_layer.items():
    color_tile_maps[color] = scene.layers[layer].add_tile_map()
    if color != 'gray':
        color_off_tile_maps[color] = scene.layers[layer + 1].add_tile_map()
        scene.layers[layer + 1].visible = False


class Block:
    def __init__(self, color, image, x, y=None):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        # grid[int(position.x)][int(position.y)].append(self)
        assert color in color_tile_maps, f"{color=} not in {color_tile_maps=}"
        self.color = color

        # self.shape = scene.layers[0].add_rect(cell_size, cell_size, fill=True, color='red', pos=(position.x*cell_size, position.y*cell_size))
        if image is not None:
            tile_map = color_tile_maps[color]
            tile_map[x, y] = image

            if color != 'gray':
                tile_map = color_off_tile_maps[color]
                tile_map[x, y] = f"{color}_off_20"

        level.collision_grid.add(self)
        self.solid = True
        level.color_to_shapes[color].append(self)

    def __repr_pos__(self):
        return f"({int(self.pos.x):3}, {int(self.pos.y):3})"

    def __repr__(self):
        return f"<Block {self.__repr_pos__()} {self.color}>"

    def on_touched(self):
        pass

class Death(Block):
    solid = True
    color = 'gray'

    def __init__(self, x, y=None):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        level.collision_grid.add(self)

    def __repr__(self):
        return f"<Death {self.__repr_pos__()}>"

    def on_touched(self):
        player.nursery.cancel()


class Checkpoint(Block):
    deselected_image = "pixel_platformer/tiles/tile_0128"
    selected_image = "pixel_platformer/tiles/tile_0129"

    def __init__(self, image, x, y=None, *, initial=False):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        # grid[int(position.x)][int(position.y)].append(self)
        # tile_map = gray_tile_map
        # tile_map[x, y] = image
        self.sprite = scene.layers[gray_layer].add_sprite(self.deselected_image, pos=self.pos * TILE_SIZE, anchor_x=0, anchor_y=0)

        level.collision_grid.add(self)
        self.solid = False

        if initial:
            self.on_touched()

    def on_touched(self):
        if level.current_checkpoint != self:
            if level.current_checkpoint:
                level.current_checkpoint.on_deselected()
            level.current_checkpoint = self
            self.sprite.image = self.selected_image

    def __repr__(self):
        current = "current" if level.current_checkpoint == self else "unselected"
        return f"<Checkpoint {self.__repr_pos__()} {current}>"

    def on_deselected(self):
        self.sprite.image = self.deselected_image


class Collectable(Block):
    nursery: w2d.Nursery

    def __init__(self, image: str, x, y=None):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)

        self.image = image
        self.pos = position
        self.collected = False

        level.collision_grid.add(self)
        self.solid = False

    def __repr__(self):
        current = "collected" if self.collected == self else "uncollected"
        return f"<Collectable {self.__repr_pos__()} {current}>"

    def on_touched(self):
        self.collected = True
        self.nursery.cancel()

    async def run(self):
        sprite = w2d.Group([
                scene.layers[sprite_layer].add_sprite(
                    self.image,
                    anchor_x=0,
                    anchor_y=0
                ),
                lights.add_sprite(
                    'point_light',
                    pos=TILE_DIMS / 2,
                    color=(1, 1, 1, 0.3),
                ),
            ],
            pos=self.pos * TILE_SIZE,
        )
        with sprite:
            level.collectables += 1
            try:
                async with w2d.Nursery() as self.nursery:
                    self.nursery.do(floating_wobble(sprite))
            finally:
                level.collectables -= 1


async def floating_wobble(
    sprite,
    *,
    speed: float = 10.0,
    pixels: float = 3.0,
):
    phase = random.random() * math.tau
    wobble_range = vec2(0, pixels)
    starting_pos = sprite.pos

    async for t in game_clock.coro.frames():
        sprite.pos = starting_pos + wobble_range * math.sin(speed * t + phase)


class Switch(Block):
    def __init__(self, color, x, y=None):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        # grid[int(position.x)][int(position.y)].append(self)
        # tile_map = gray_tile_map
        # tile_map[x, y] = image

        self.color = color
        self.on_image = f"{color}_switch_on"
        self.off_image = f"{color}_switch_off"

        level.collision_grid.add(self)
        self.solid = False

        self.sprite = w2d.Group([
                scene.layers[sprite_layer].add_sprite(self.on_image, anchor_x=0, anchor_y=0),
                lights.add_sprite(
                    'point_light',
                    color=(*color_to_rgb[color], 1),
                    pos=TILE_DIMS / 2,
                )
            ],
            pos=self.pos * TILE_SIZE,
        )
        # set initial wobble

    def __repr__(self):
        current = "on" if self.sprite[0].image == self.on_image else "off"
        return f"<Switch {self.__repr_pos__()} {self.color} {current}>"

    def on_touched(self):
        new_state = level.toggle_color(self.color)
        sprite, light = self.sprite
        if new_state:
            sprite.image = self.on_image
            light.alpha = 1.0
        else:
            sprite.image = self.off_image
            light.alpha = 0.6


def background_block(image, x, y=None):
    if (y is None) and isinstance(x, vec2):
        x, y = x
    tile_map = background_tile_map
    tile_map[x, y] = image


actions = {
    "move_up",
    "move_down",
    "move_left",
    "move_right",

    "jump,"
    "shoot",
    "pause",
    "quit",

    "toggle_red",
    "toggle_orange",
    "toggle_yellow",
    "toggle_green",
    "toggle_blue",
    "toggle_purple",
    }


cell_size = TILE_SIZE

background_tile_map = scene.layers[background_layer].add_tile_map()
gray_tile_map = color_tile_maps['gray']

main_clock = Clock()
game_clock = main_clock.create_sub_clock()


class Level:
    def __init__(self):
        self.color_state = {color: True for color in colors}
        self.color_to_shapes = {color: [] for color in colors}

        self.collectables = 0

        self.current_checkpoint = None
        self.physical_objects = {}

    async def run(self):
        global player
        objects = self.load_map("test")
        async with w2d.Nursery() as self.nursery:
            for obj in objects:
                self.nursery.do(obj.run())
            self.nursery.do(run_lives())

    def toggle_color(self, color):
        assert color != "gray"
        old_state = self.color_state[color]
        new_state = not old_state
        self.color_state[color] = new_state
        scene.layers[color_to_layer[color]].visible = new_state
        scene.layers[color_to_layer[color] + 1].visible = old_state

        return new_state

    def load_map(self, name):
        filename = f"level_{name}.tmx"
        level_map = parse_map(gamedir_path.joinpath("data", filename))

        self.map_size = vec2(level_map.map_size)
        self.map_size_in_screen = self.map_size * TILE_SIZE

        # print(f"loaded map, size {self.map_size}")

        self.collision_grid = collision.GridCollider(self.map_size + vec2(2, 2), origin=vec2(-1, -1))

        # don't ever let the player leave the map.
        # add a perimeter of blocks around the level:
        #
        #  bbbbbbbbbbbbbbbb
        #  b              b
        #  b              b  <-'b' means a normal Block
        #  b              b
        #  XXXXXXXXXXXXXXXX  <-'X' means a Death block

        upper_left = self.collision_grid.upper_left
        lower_right = self.map_size
        # print(f"{upper_left=}")
        # print(f"{lower_right=}")
        y = int(upper_left.y)
        for x in range(int(upper_left.x), int(lower_right.x) + 1):
            # blocks add themselves to the collision grid
            b = Block("gray", None, x, y)
            # print("added top barrier", b)

        x_left = int(upper_left.x)
        x_right = int(lower_right.x)
        for y in range(int(upper_left.y + 1), int(lower_right.y)):
            b = Block("gray", None, x_left, y)
            # print("added left barrier", b)
            b = Block("gray", None, x_right, y)
            # print("added right barrier", b)

        y = int(lower_right.y)
        for x in range(int(upper_left.x), int(lower_right.x) + 1):
            b = Death(x, y)
            # print("added bottom barrier", b)

        global scene_camera_bounding_box
        scene_camera_bounding_box = wasabigeom.Rect(
            scene_width / 2, # left
            self.map_size_in_screen.x - (scene_width / 2), # right
            scene_height / 2, # bottom
            self.map_size_in_screen.y - (scene_height / 2), # top
            )

        tiles = {}

        offset = 0
        for tileset in level_map.tilesets.values():
            max_id = -1
            for id, tile in tileset.tiles.items():
                id += offset
                # print(f"{tileset.name} {id} -> tile {tile.image}")
                tiles[id] = tile
                max_id = max(id, max_id)
            offset = max_id

        empty_dict = {}

        objects = []
        for layer in level_map.layers:
            block_type_override = None
            if layer.name == "Background":
                scene_layer = scene.layers[background_layer]
                block_type_override = background_block
            elif layer.name == "Terrain":
                scene_layer = scene.layers[gray_layer]
            else:
                assert None, "unhandled layer name"

            for y, column in enumerate(layer.data):
                for x, tile_id in enumerate(column):
                    # print(f"{x=} {y=} {tile_id=}")
                    if not tile_id:
                        continue
                    tile_id -= 1 # OMG DID YOU JUST DO THIS TO ME PYTILED_PARSER
                    tile = tiles[tile_id]
                    image = tile.image.replace('/', os.sep)
                    assert image

                    if block_type_override:
                        background_block(image, x, y)
                        continue

                    properties = tile.properties or empty_dict
                    object_type = tile.properties.get("object", None)
                    color = tile.properties.get("color", "gray")

                    if object_type == "checkpoint":
                        checkpoint = tile.properties.get("checkpoint", None)
                        initial = checkpoint == "selected"
                        block = Checkpoint(image, x, y, initial=initial)
                        if initial:
                            self.current_checkpoint = block
                    elif object_type == "gem":
                        block = Collectable(image, x, y)
                    elif object_type == "switch":
                        block = Switch(color, x, y)
                    else:
                        block = Block(color, image, x, y)
                    if hasattr(block, 'run'):
                        objects.append(block)

        assert self.current_checkpoint, "no initial checkpoint set in map!"
        return objects



player_max_jumps = 2
player_max_dashes = 1


class Controller:
    KEYBOARD = w2d.keyboard.keyboard

    def x_axis(self) -> float:
        """Get the x position of the "stick", from -1 to 1."""
        return (
            (self.KEYBOARD.right or self.KEYBOARD.d)
            - (self.KEYBOARD.left or self.KEYBOARD.a)
        )

    async def jump(self):
        """Await the player pressing the jump key."""
        await w2d.next_event(pygame.KEYDOWN, key=w2d.keys.SPACE.value)

    async def shoot(self):
        """Await the player pressing the shoot key."""
        await w2d.next_event(pygame.KEYDOWN, key=w2d.keys.RETURN.value)


async def shoot(player: 'Player', direction: vec2):
    """Fire a shot."""
    SPEED = 30

    rgb = (1, 1, 1)

    pos = player.pos + vec2(0.5, 0.5)
    sprite = w2d.Group([
            laser := scene.layers[player_layer].add_sprite(
                'laser',
                angle=direction.angle(),
                color=(*rgb, 0),
            ),
            light := lights.add_sprite(
                'point_light',
                color=(*rgb, 0),
                scale=0.3,
            )
        ],
        pos=pos * TILE_SIZE,
    )

    async def animate_pos():
        nonlocal pos
        assert level

        touching = set()
        async for dt in game_clock.coro.frames_dt(seconds=2):
            delta = direction * SPEED * dt
            collisions = level.collision_grid.collide_moving_point(pos, delta)

            new_touching = set()
            for t, loc, hits in collisions:
                for obj in hits:
                    match obj:
                        case Switch():
                            if obj not in touching:
                                obj.on_touched()
                            new_touching.add(obj)

                        case Block():
                            ns.cancel()

            pos += delta
            sprite.pos = pos * TILE_SIZE
            touching = new_touching

    async def animate_color(obj, max=1):
        await w2d.animate(obj, color=(*rgb, max), duration=0.2)
        await game_clock.coro.sleep(0.4)
        await w2d.animate(obj, color=(*rgb, 0), duration=1.4)

    with sprite:
        async with w2d.Nursery() as ns:
            ns.do(animate_pos())
            ns.do(animate_color(laser))
            ns.do(animate_color(light, max=0.3))
            ns.do(w2d.animate(light, scale=1, duration=0.4))


async def puff(pos: vec2, vel: vec2 = vec2(0, -8)):
    """Draw a puff of smoke.

    The supplied pos/vel are in world space coordinates, i.e. pixels.
    """
    with scene.layers[sprite_layer].add_sprite(
        'smoke',
        scale=0.2,
        pos=pos,
    ) as sprite:
        await w2d.animate(
            sprite,
            duration=0.5,
            tween='accelerate',
            color=(1, 1, 1, 0),
            pos=pos + vel,
            scale=0.5,
        )


class Player:
    size = vec2(1, 1)

    def __init__(self, pos: vec2, controller: Controller):
        self.v = vec2(0, 0)
        self.facing = 1
        self.shape = scene.layers[player_layer].add_sprite("pixel_platformer/tiles/tile_0145", pos=pos * TILE_SIZE, anchor_x=0, anchor_y=0)
        # self.shape = scene.layers[player_layer].add_star(
        #     pos=pos * TILE_SIZE,
        #     points=6,
        #     outer_radius=cell_size / 2, inner_radius=cell_size / 4, fill=True, color=(0.5, 0.5, 0.5)
        # )

        scene.camera.pos = self.shape.pos

        self.controller = controller
        self._jumps_remaining = 2

    async def handle_keys(self):
        key_to_action = {
            w2d.keys.K_1: "red",
            w2d.keys.K_2: "orange",
            w2d.keys.K_3: "yellow",
            w2d.keys.K_4: "green",
            w2d.keys.K_5: "blue",
            w2d.keys.K_6: "purple",
        }

        async for ev in w2d.events.subscribe(pygame.KEYDOWN, pygame.KEYUP):
            key = w2d.constants.keys(ev.key)
            if not (color := key_to_action.get(key)):
                continue
            if ev.type == pygame.KEYDOWN:
                level.toggle_color(color)

    async def run(self):
        with self.shape:
            async with w2d.Nursery() as ns:
                self.nursery = ns
                ns.do(self.accel())
                ns.do(self.jump())
                ns.do(self.shoot())
                ns.do(self.run_physics())
                ns.do(self.camera_tracking())
                ns.do(self.handle_keys())

    async def shoot(self):
        while True:
            await self.controller.shoot()
            level.nursery.do(shoot(self, vec2(self.facing, 0)))
            await game_clock.coro.sleep(0.15)

    async def accel(self):
        """Accelerate the player, including in the air."""
        async for _ in game_clock.coro.frames():
            x_axis = self.controller.x_axis()
            speed_x = self.v.x
            if x_axis:
                self.facing = math.copysign(1.0, x_axis)
                acceleration = self.controller.x_axis() * self.ACCEL_FORCE
                speed_x += acceleration
                speed_x = min(max(speed_x, -self.MAX_HORIZONTAL_SPEED), self.MAX_HORIZONTAL_SPEED)
            elif self.state == self.state_on_ground:
                speed_x *= self.GROUND_FRICTION_FACTOR
                if abs(speed_x) < 0.005:
                    speed_x = 0
            self.v = vec2(speed_x, self.v.y)

    async def jump(self):
        while True:
            await self.controller.jump()
            if self._jumps_remaining:
                # print(f"--- jump start ---")
                self.v += self.JUMP
                self.state = self.state_start_jump
                self.jump_start_pos = self.pos
                self._jumps_remaining -= 1

                level.nursery.do(puff(
                    self.shape.pos + vec2((-self.v.x + 0.5) * TILE_SIZE, TILE_SIZE),
                    vel=vec2(-2 * TILE_SIZE * self.v.x, 5)
                ))

    # Cells per second
    JUMP = vec2(0, -0.27)

    # Cells per second per second
    RISING_GRAVITY = vec2(0, 0.8)

    # Cells per second per second
    FALLING_GRAVITY = vec2(0, 1.1)

    #                   vvv cells per second
    TERMINAL_VELOCITY = 20.0 / 60
    #                        ^^^^ divide by ticks per second (aka multiply by seconds per tick)
    # so this is cells per tick.

    ACCEL_FORCE = 0.01

    MAX_HORIZONTAL_SPEED = 0.4

    GROUND_FRICTION_FACTOR = 0.82 # delta.x multiplied by this every tick

    WALL_FRICTION_MAX_SPEED = TERMINAL_VELOCITY / 5

    #                      vvvv  hang time in seconds
    HANG_TIME_TICKS = int( 0.07 * 60 )
    #                           ^^^^ times ticks per second

    #                        vvvv  coyote time in seconds
    COYOTE_TIME_TICKS = int( 0.05 * 60 )
    #                             ^^^^ times ticks per second

    state_start_jump = "start jump"
    state_rising = "rising"
    state_hang_time = "hang time"
    state_falling = "falling"
    state_on_ground = "on ground"
    state_coyote_time = "coyote time"

    @property
    def pos(self) -> vec2:
        """Get the position of the player in tile coordinates."""
        return self.shape.pos / TILE_SIZE

    @pos.setter
    def pos(self, v: vec2):
        """Get the position of the player in tile coordinates."""
        self.shape.pos = v * TILE_SIZE

    async def run_physics(self):
        tick = 0
        dt = 1/60
        death_plane = level.map_size.y
        rising_gravity = self.RISING_GRAVITY * dt
        falling_gravity = self.FALLING_GRAVITY * dt

        self.state = self.state_on_ground
        assert self._jumps_remaining == 2

        jumped = False

        coyote_time_until = 0

        # The set of things we are already touching.
        # We only fire on_touched() events for objects that we are newly
        # touching.
        touching = set()

        def print(*a): pass
        # print = builtins.print

        # HACK FOR DEBUG
        if 0:
            self.pos = vec2(+0.34889, +20.53333)
            self.v = vec2(-0.35374, -0.20667)
            self.state = self.state_rising

            hang_time_timer = self.HANG_TIME_TICKS
            self.jump_start_pos = self.pos


        async for _ in game_clock.coro.frames():
            tick += 1
            print(f"[{tick:05} start] {self.state:12} pos=({self.pos.x:+1.5f}, {self.pos.y:+1.5f}) delta=({self.v.x:+1.5f}, {self.v.y:+1.5f})")

            if 1:
                hits = level.collision_grid.collide_pawn(self)
                if hits:
                    solid_hits = [tile for tile in hits if tile.solid and level.color_state[tile.color]]
                    if solid_hits:
                        print = builtins.print
                        print(f"shouldn't be touching anything solid right now!")
                        print(f"pawn {self.pos=} {self.v=}")
                        print("tiles:")
                        for tile in solid_hits:
                            print(f"  {tile} {tile.pos}")
                        sys.exit(0)

            delta = self.v

            if self.state == self.state_start_jump:
                self.state = self.state_rising
                jump_start_tick = tick
                gravity = rising_gravity
            elif self.state == self.state_rising:
                gravity = rising_gravity
            elif self.state == self.state_hang_time:
                gravity = vec2_zero
                delta = vec2(delta.x, 0)
            else:
                gravity = falling_gravity
                if self.state == self.state_coyote_time:
                    if tick >= coyote_time_until:
                        self.state = self.state_falling
                        if self._jumps_remaining == 2:
                            self._jumps_remaining = 1


            delta += gravity

            if self.state == self.state_rising:
                if delta.y >= 0:
                    self.state = self.state_hang_time
                    hang_time_timer = self.HANG_TIME_TICKS
                    hang_time_start_tick = tick
                    max_height = abs(self.pos.y - self.jump_start_pos.y)
                    jumped = True
            elif self.state == self.state_hang_time:
                hang_time_timer -= 1
                if not hang_time_timer:
                    self.state = self.state_falling
                    falling_time_start_tick = tick
            else:
                if delta.y > self.TERMINAL_VELOCITY:
                    delta = vec2(delta.x, self.TERMINAL_VELOCITY)

            starting_pos = self.pos
            checking_for_collisions = True

            found_a_solid_collision = False
            delta_remaining = delta

            while checking_for_collisions:
                for t, collision_pos, hit in level.collision_grid.collide_moving_pawn(
                    self,
                    delta_remaining,
                ):
                    solid_tiles = []
                    passthrough_tiles = set()

                    for tile in hit:
                        assert hasattr(tile, 'solid')
                        if tile.solid:
                            if level.color_state[tile.color]:
                                solid_tiles.append(tile)
                        else:
                            passthrough_tiles.add(tile)

                    if not solid_tiles:
                        print(f"{t=} collision with only passthrough tiles.")
                        for tile in passthrough_tiles - touching:
                            tile.on_touched()
                        touching = passthrough_tiles
                        continue

                    found_a_solid_collision = True
                    # okay, this collision will change our movement.
                    t_just_barely_before_the_collision = math.nextafter(t, -math.inf)
                    self.pos += (delta_remaining * t_just_barely_before_the_collision)

                    print("collision with solid tiles:")
                    print(f"    {collision_pos=}")

                    # old collision detection trick.
                    # do two lines overlap?  it's easy.
                    #
                    # consider all the possible relationships the two lines could
                    # have to each other, and whether or not they are touching.
                    #
                    # legend:
                    #     ---- line 1
                    #     ==== line 2
                    #
                    # scenario 1: line 1 completely to the left - NOT TOUCHING
                    #        -----
                    #              ======
                    #
                    # scenario 2: line 1 overlapping on the left - touching
                    #        --------
                    #              ======
                    #
                    # scenario 3: line 1 completely the same - touching
                    #              ------
                    #              ======
                    #
                    # scenario 4: line 2 is entirely inside line 1 - touching
                    #              ------
                    #               ====
                    #
                    # scenario 5: line 1 is entirely inside line 2 - touching
                    #              -----
                    #             =======
                    #
                    # scenario 6: line 1 overlapping on the right - touching
                    #              ----------
                    #             =======
                    #
                    # scenario 7: line 1 completely to the right - NOT TOUCHING
                    #                      -------
                    #             =======
                    #
                    # now notice: they are not touching in the first and last scenarios,
                    # and touch in every other scenario.  So: test for the first and
                    # last scenarios, and if neither of those are true, they're touching,
                    # and you probably don't care in what way.

                    # special-cased for this game
                    assert self.size == vec2(1, 1)
                    def pawn_overlaps_tile_in_x(tile):
                        return not ( ((self.pos.x + 1) <= tile.pos.x) or (self.pos.x >= (tile.pos.x + 1)) )
                    def pawn_overlaps_tile_in_y(tile):
                        return not ( ((self.pos.y + 1) <= tile.pos.y) or (self.pos.y >= (tile.pos.y + 1)) )

                    hit_corner = hit_x = hit_y = False

                    for tile in solid_tiles:
                        tile.on_touched()

                        # these are all calculated based on the just-before-collision position.
                        tile_overlaps_in_x = pawn_overlaps_tile_in_x(tile)
                        tile_overlaps_in_y = pawn_overlaps_tile_in_y(tile)
                        print(f"    {tile.pos=} {tile=} {tile_overlaps_in_x=} {tile_overlaps_in_y=}")

                        if tile_overlaps_in_x:
                            hit_y = True
                            assert not tile_overlaps_in_y
                        elif tile_overlaps_in_y:
                            hit_x = True
                            assert not tile_overlaps_in_x
                        else:
                            # neither
                            assert not (tile_overlaps_in_x or tile_overlaps_in_y)
                            hit_corner = True

                    if hit_x:
                        # if we hit multiple tiles, and one was a hit in x,
                        # and another was corner, ignore the corner.
                        hit_corner = False

                    if hit_y:
                        # if we hit multiple tiles, and one was a hit in y,
                        # and another was corner, ignore the corner.
                        hit_corner = False

                    if hit_corner:
                        # we must have only hit one tile, and it was a corner.
                        # we must be moving in both x and y.
                        # y is more important, so we behave like
                        # this is hitting floor/ceiling.
                        assert len(solid_tiles) == 1
                        assert bool(delta_remaining.x) and bool(delta_remaining.y)
                        assert not (hit_x or hit_y)
                        hit_y = True
                        print("hit corner, so {hit_x=} {hit_y=}")

                    if hit_x:
                        # stop sideways motion
                        # but also! cap vertical motion ("wall scrape")
                        print("  hit in x, stop sideways motion, also cap vertical motion ('wall scrape')")
                        print(f"    before hit in x: {delta=} {delta_remaining}  {self.WALL_FRICTION_MAX_SPEED=}")
                        max_y_velocity = self.WALL_FRICTION_MAX_SPEED

                        # wall scrape ONLY affects downward speed.
                        # reminder: coordinate system has 0 at TOP left
                        # so delta.y >= means falling.
                        delta_remaining_y = delta_remaining.y
                        delta_y = delta.y
                        if delta_remaining_y > 0:
                            assert delta_y > 0
                            t_remaining = delta_remaining_y / delta_y
                            delta_remaining_y = min(delta_remaining_y, max_y_velocity * t_remaining)
                            delta_y = min(delta_y, max_y_velocity)
                        delta_remaining = vec2(0, delta_remaining_y)
                        delta = vec2(0, delta_y)
                        print(f"    after hit in x: {delta=} {delta_remaining}")

                    if hit_y:
                        # stop vertical motion
                        print("  hit in y, stop vertical motion")
                        if self.state == self.state_falling:
                            assert delta.y > 0
                            assert delta_remaining.y > 0
                            self.state = self.state_on_ground
                            self._jumps_remaining = 2

                            if jumped:
                                jumped = False
                                rising_time = (hang_time_start_tick - jump_start_tick) * dt
                                assert (falling_time_start_tick - hang_time_start_tick) == self.HANG_TIME_TICKS, f"({falling_time_start_tick=} - {hang_time_start_tick=}) != {self.HANG_TIME_TICKS=} !!!"
                                hang_time = self.HANG_TIME_TICKS * dt
                                falling_time = (tick - falling_time_start_tick) * dt
                                total_jump_time = rising_time + hang_time + falling_time
                                print("  jump stats:")
                                print(f"  {rising_time     = :1.5f}")
                                print(f"  {hang_time       = :1.5f}")
                                print(f"  {falling_time    = :1.5f}")
                                print(f"  {total_jump_time = :1.5f}")
                                print()

                                print(f"{max_height      = :1.5f}")
                                # sys.exit(0)

                        # stop vertical motion
                        delta = vec2(delta.x, 0)
                        delta_remaining = vec2(delta_remaining.x, 0)

                    if delta == vec2_zero:
                        assert delta_remaining == vec2_zero, f"{delta_remaining=} != vec2_zero!"
                        checking_for_collisions = False
                else:
                    checking_for_collisions = False

                if (not found_a_solid_collision) and (self.state == self.state_on_ground):
                    # hey, wait! we're supposed to always collide with the ground!
                    # we must have fallen off the edge!
                    self.state = self.state_coyote_time
                    coyote_time_until = tick + self.COYOTE_TIME_TICKS
                    assert self._jumps_remaining == 2
                    self._jumps_remaining = 1

                self.pos += delta

            print(f"[{tick:05}   end] {self.state:12} pos=({self.pos.x:+1.5f}, {self.pos.y:+1.5f}) {delta.y=:+2.5f}")

            # check if the player has fallen below the death plane
            # if self.pos.y >= death_plane:
            #     # death!
            #     self.nursery.cancel()

            # print(f"[{tick:06}] final {delta=}")
            self.v = delta

    async def camera_tracking(self):
        last_pos = target_pos = self.shape.pos
        target_offset = vec2(0, 0)

        # cwbb_factor defines how big the cwbb is around the player.
        # the larger the number, the larger the cwbb.
        #
        # 1/6 means the camera can only move 1/6 of the screen
        # away from the player before being constrained.
        #
        # 1 means it's the size of the entire viewport.
        # 0 means it has zero size.
        #
        # you're encouraged to use a fraction.
        cwbb_factor = 1/5

        # cwbb_factor = (1 - cwbb_factor)
        # cwbb is in screen coords
        CWBB = wasabigeom.Rect(
            -scene_width  * cwbb_factor, # l
            +scene_width  * cwbb_factor, # r
            -scene_height * cwbb_factor, # b
            +scene_height * cwbb_factor, # t
        )

        async for dt in game_clock.coro.frames_dt():
            # Although it's not explicitly guaranteed by wasabi2d
            # and its -> *async* <- coroutines, in fact this will
            # always be run *after* run_physics() computes its
            # physics step for a given logical frame.

            # adjust camera based on player position
            # (the player no longer stores its own position,
            #  it's only represented in PyMunk in tile space
            #  and onscreen in screen space)
            #
            # Imagine the worldspace (in tile coordinates)
            # as a big rectangle.  Now imagine the screen is
            # a window into that rectangle.
            #
            #    +-----------------------+
            #    |world                  |
            #    |  +------+             |
            #    |  |screen|             |
            #    |  |      |             |
            #    |  +------+             |
            #    |                       |
            #    +-----------------------+
            #
            # There's a point at the dead center of the "screen",
            # we're going to call the "camera".
            #
            # Under normal circumstances, during gameplay the
            # player is moving.  There's an imaginary box around
            # the player called the "camera weak bounding box" or
            # cwbb.
            #
            # When the player moves, the cwbb moves in the
            # same direction but twice as far.  This means the camera
            # races ahead of the player, so you can see where you're
            # going.
            #
            # If after moving, the camera is still inside the cwbb,
            # that's fine.  But if the camera is now outside the cwbb,
            # it's moved until it's inside, along either or both the
            # X and Y axes.
            #
            # But then!  If the camera's new position would make the
            # screen extend past the edges of the world, the camera
            # is moved once more so that the screen remains inside
            # the world, again along either or both the X and Y axes.
            #
            # When initially setting up the level, the camera
            # is dropped on the player, and then the camera is
            # moved if the screen extends past the edge of the world.
            screen_delta: vec2 = self.shape.pos - last_pos
            if not screen_delta.is_zero():
                last_pos = self.shape.pos

                target_offset = target_offset * 0.95 + 2 * screen_delta
                target_pos = self.shape.pos + target_offset

                cwbb = CWBB.translate(self.shape.pos)

                # print(f"1. {screen_pos=}")
                # print(f"   {cwbb=}")
                # print(f"   {camera=}")
                if not cwbb.contains(target_pos):
                    x, y = target_pos
                    if x < cwbb.l:
                        x = cwbb.l
                    elif x > cwbb.r:
                        x = cwbb.r
                    if y < cwbb.b:
                        y = cwbb.b
                    elif y > cwbb.t:
                        y = cwbb.t
                    target_pos = vec2(x, y)
                    # print(f"   adjusted to {camera}")

            camera = scene.camera.pos * 0.95 + target_pos * 0.05

            # print(f"2. {scene_camera_bounding_box=}")
            # print(f"   {camera=}")
            if not scene_camera_bounding_box.contains(camera):
                x, y = camera
                if x < scene_camera_bounding_box.l:
                    x = scene_camera_bounding_box.l
                elif x > scene_camera_bounding_box.r:
                    x = scene_camera_bounding_box.r
                if y < scene_camera_bounding_box.b:
                    y = scene_camera_bounding_box.b
                elif y > scene_camera_bounding_box.t:
                    y = scene_camera_bounding_box.t
                camera = vec2(x, y)
                # print(f"   adjusted to {camera}")

            # print(f"3. final screen {camera=}")
            # print()
            scene.camera.pos = camera


async def run_lives():
    controller = Controller()
    for _ in range(3):
        pos = level.current_checkpoint.pos
        global player
        player = Player(pos, controller)
        await player.run()


async def drive_main_clock():
    # convert time into ticks.
    # there are sixty ticks per second.
    #
    # the basic idea:
    #    whenever wasabi calls us, compare the last
    #    time to the current time.  for every 1/60s
    #    threshold that has elapsed since last time
    #    wasabi called us, send a tick to the game clock.
    #
    tick_offsets = [(i+1)/60 for i in range(60)]
    one_sixtieth = 1/60

    # if we fall behind more than this many ticks,
    # just send in this many ticks and continue.
    max_ticks = 6

    next_tick_seconds, fractional = 0, 0
    next_tick_index = bisect.bisect(tick_offsets, fractional)
    next_tick_fractional = tick_offsets[next_tick_index]

    async for t in wasabi2d.clock.coro.frames():
        assert t >= next_tick_seconds
        fractional = t - next_tick_seconds
        ticks = 0
        while fractional >= next_tick_fractional:
            ticks += 1
            if ticks <= max_ticks:
                main_clock.tick(one_sixtieth)

            next_tick_index += 1
            if next_tick_index == 60:
                assert next_tick_fractional == 1
                next_tick_index = 0
                fractional -= 1
                next_tick_seconds += 1
            next_tick_fractional = tick_offsets[next_tick_index]


async def pauser():
   while True:
        await w2d.next_event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        paused = game_clock.paused = not game_clock.paused
        if paused:
            for layer in layers:
                scene.layers[layer].set_effect('blur')
        else:
            for layer in layers:
                scene.layers[layer].clear_effect()


async def main():
    global level
    level = Level()
    async with w2d.Nursery() as ns:
        ns.do(drive_main_clock())
        ns.do(pauser())
        ns.do(level.run())


w2d.run(main())
