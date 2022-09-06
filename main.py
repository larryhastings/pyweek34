import bisect
import collections
from contextlib import contextmanager
import math
from pathlib import Path
import pymunk
from pytiled_parser import parse_map
import random
import sys
from typing import Any, Generator
import typing
import wasabi2d.loop
from wasabi2d.clock import Clock
import wasabi2d as w2d
import wasabigeom
from wasabigeom import vec2

# import after wasabi2d, this suppresses the PyGame stdout message
import pygame


TILE_SIZE: int = 18
FRICTION: float = 0
GRAVITY: float = 20

game = None
level = None
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

scene_width = 900
scene_height = 540

scene_camera_bounding_box = None

scene = w2d.Scene(scene_width, scene_height)
scene.background = (0.9, 0.9, 0.9)

space = pymunk.Space()      # Create a Space which contain the simulation
space.gravity = 0, GRAVITY      # Set its gravity


def on_player_collided(
    arbiter: pymunk.Arbiter,
    space: pymunk.Space,
    data: Any,
) -> bool:

    if not arbiter.is_first_contact:
        return True

    a, b = arbiter.shapes

    game_object = getattr(b, "game_object", None)
    if game_object:
        game_object.on_touched()

    is_down = 89 < arbiter.normal.angle_degrees < 91
    if is_down:
        player = a.body.player
        player._add_floor()
    data['on_ground'] = is_down

    # Handle this collision normally
    return True


def on_player_separate(
    arbiter: pymunk.Arbiter,
    space: pymunk.Space,
    data: Any,
) -> bool:
    if data.get('on_ground'):
        player._remove_floor()
    return True


COLLISION_TYPE_PLAYER = 1
player_collision = space.add_wildcard_collision_handler(COLLISION_TYPE_PLAYER)
player_collision.begin = on_player_collided
player_collision.separate = on_player_separate


def create_body(
    pos: vec2,
    size: tuple[int, int] = (1, 1),
    mass: float = 10.0
) -> pymunk.Body:
    """Create a square dynamic body."""
    body = pymunk.Body(mass, float('inf'))
    body.position = tuple(pos + vec2(size) / 2)

    poly = pymunk.Poly.create_box(
        body,
        size=size,
        radius=0.1,
    )
    poly.friction = FRICTION
    poly.elasticity = 0
    space.add(body, poly)
    return body


def create_static(
    pos: vec2,
    size: tuple[int, int] = (1, 1),
    *,
    sensor=False
) -> pymunk.Shape:
    """Create a static body centred at the given position."""
    hw, hh = vec2(size) / 2

    # There's no way to position a pymunk shape after creation so we create it
    # at the position we want it
    coords = [
        pos + vec2(hw, hh),
        pos + vec2(hw, -hh),
        pos + vec2(-hw, -hh),
        pos + vec2(-hw, hh),
    ]
    poly = pymunk.Poly(space.static_body, [tuple(c) for c in coords])
    if sensor:
        poly.sensor = True
    else:
        poly.friction = FRICTION
        poly.elasticity = 0

    space.add(poly)
    return poly


class Positionable(typing.Protocol):
    pos: vec2



@contextmanager
def physical(
    drawn: Positionable,
    mass: float = 10,
) -> Generator[pymunk.Body, None, None]:
    """Treat an object as physical within the context.

    Yield a body on which to apply forces/impulses etc.
    """
    body = create_body(drawn.pos / TILE_SIZE, mass=mass)
    try:
        with drawn:
            level.physical_objects[body] = drawn
            yield body
    finally:
        space.remove(body, *body.shapes)
        del level.physical_objects[body]



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
        tile_map = color_tile_maps[color]
        tile_map[x, y] = image

        if color != 'gray':
            tile_map = color_off_tile_maps[color]
            tile_map[x, y] = f"{color}_off_20"

        self.shape = create_static(position)
        level.color_to_shapes[color].append(self.shape)



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
        self.shape = create_static(position, sensor=True)
        self.shape.game_object = self

        if initial:
            self.on_touched()

    def on_touched(self):
        if level.current_checkpoint != self:
            if level.current_checkpoint:
                level.current_checkpoint.on_deselected()
            level.current_checkpoint = self
            self.sprite.image = self.selected_image

    def on_deselected(self):
        self.sprite.image = self.deselected_image


class Collectable(Block):
    def __init__(self, image, x, y=None):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        # grid[int(position.x)][int(position.y)].append(self)
        # tile_map = gray_tile_map
        # tile_map[x, y] = image

        self.wobble = random.random() * math.tau
        self.wobble_range = 3 # in pixels
        self.wobble_increment = 1/120 * math.tau
        self.starting_pos = pos=self.pos * TILE_SIZE
        self.sprite = scene.layers[sprite_layer].add_sprite(image, pos=self.starting_pos, anchor_x=0, anchor_y=0)
        # set initial wobble
        self.animate()
        level.animated_objects.append(self)

        self.shape = create_static(position, sensor=True)
        self.shape.game_object = self
        level.collectables += 1

    def on_touched(self):
        level.collectables -= 1
        self.sprite.delete()

    def animate(self):
        self.wobble += self.wobble_increment
        while self.wobble > math.tau:
            self.wobble -= math.tau
        pos = vec2(self.starting_pos.x, self.starting_pos.y + (self.wobble_range * math.sin(self.wobble)))
        self.sprite.pos = pos



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

    physical_objects: dict[pymunk.Body: Positionable]

    def __init__(self):
        self.color_state = {color: True for color in colors}
        self.color_to_shapes = {color: [] for color in colors}

        self.collectables = 0

        self.current_checkpoint = None
        self.physical_objects = {}
        self.animated_objects = []


    async def run_physics(self):
        """Step the Pymunk physics simulation."""
        async for dt in game_clock.coro.frames_dt():
            space.step(dt)
            for body, positionable in self.physical_objects.items():
                positionable.pos = body.position * TILE_SIZE

    async def animate(self):
        async for dt in game_clock.coro.frames_dt():
            for o in self.animated_objects:
                o.animate()


    async def run(self):
        global player
        level.load_map("test")
        player = Player(controller=Controller())
        async with w2d.Nursery() as ns:
            ns.do(self.run_physics())
            ns.do(self.animate())
            ns.do(player.run(start_pos=self.current_checkpoint.pos))


    def toggle_color(self, color):
        old_state = self.color_state[color]
        new_state = not self.color_state[color]
        self.color_state[color] = new_state
        scene.layers[color_to_layer[color]].visible = new_state
        scene.layers[color_to_layer[color] + 1].visible = old_state

        if not new_state:
            space.remove(*self.color_to_shapes[color])
        else:
            space.add(*self.color_to_shapes[color])

    def load_map(self, name):
        filename = f"level_{name}.tmx"
        level_map = parse_map(gamedir_path.joinpath("data", filename))

        self.map_size = vec2(level_map.map_size)
        self.map_size_in_screen = self.map_size * TILE_SIZE

        global scene_camera_bounding_box
        scene_camera_bounding_box = wasabigeom.Rect(
            scene_width / 2, # left
            self.map_size_in_screen.x - (scene_width / 2), # right
            scene_height / 2, # bottom
            self.map_size_in_screen.y - (scene_height / 2), # top
            )

        assert len(level_map.tilesets) == 1
        for value in level_map.tilesets.values():
            tileset = value
            break

        empty_dict = {}

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
                    tile = tileset.tiles[tile_id]
                    image = tile.image
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
                    else:
                        block = Block(color, image, x, y)

        assert self.current_checkpoint, "no initial checkpoint set in map!"



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


class Player:
    on_ground: w2d.Event

    def __init__(self, controller: Controller):
        self.shape = None
        self.speed = vec2(0, 0)
        self.x_acceleration = 0
        self.desired_x_speed = 0

        self.controller = controller
        self._standing_on_count = 0
        self.on_ground = w2d.Event()

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
        self.cwbb = wasabigeom.Rect(
            -scene_width  * cwbb_factor, # l
            +scene_width  * cwbb_factor, # r
            -scene_height * cwbb_factor, # b
            +scene_height * cwbb_factor, # t
            )

    def _add_floor(self):
        self._standing_on_count += 1
        self.on_ground.set()

    def _remove_floor(self):
        self._standing_on_count -= 1
        if self._standing_on_count == 0:
            self.on_ground = w2d.Event()

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

    async def run(self, start_pos: vec2):
        screen_pos = start_pos * TILE_SIZE
        # we'll fix this before drawing in monitor_player_position
        scene.camera.pos = screen_pos
        self.shape = scene.layers[player_layer].add_star(
            pos=screen_pos,
            points=6,
            outer_radius=cell_size, inner_radius=cell_size / 2, fill=True, color=(0.5, 0.5, 0.5))
        with physical(self.shape) as self.body:
            self.body.player = self
            for shape in self.body.shapes:
                shape.collision_type = COLLISION_TYPE_PLAYER
            async with w2d.Nursery() as ns:
                self.nursery = ns
                ns.do(self.accel())
                ns.do(self.jump())
                ns.do(self.monitor_player_position())
                ns.do(self.handle_keys())

    async def accel(self):
        """Accelerate the player, including in the air."""
        async for _ in game_clock.coro.frames():
            self.body.apply_force_at_world_point(
                (self.controller.x_axis() * self.ACCEL_FORCE, 0),
                self.body.position
            )

    ACCEL_FORCE = 200.0
    JUMP_IMPULSE = (0, -100)

    async def jump(self):
        async def _jump_on_press():
            """Apply an impulse to the player body when jump is pressed."""
            await self.controller.jump()
            self.body.apply_impulse_at_local_point(self.JUMP_IMPULSE)

        while True:
            await _jump_on_press()
            async with w2d.Nursery() as ns:
                if self.on_ground.is_set():
                    ns.do(_jump_on_press())
                await self.on_ground
                ns.cancel()

    async def monitor_player_position(self):
        death_plane = level.map_size.y
        last_pos = self.body.position
        async for _ in game_clock.coro.frames():
            # Although it's not explicitly guaranteed by wasabi2d
            # and its -> *async* <- coroutines, in fact this will
            # always be run *after* run_physics() computes its
            # physics step for a given logical frame.

            # check if the player has fallen below the death plane
            pos = self.body.position
            if pos.y >= death_plane:
                # respawn!
                pos = last_pos = level.current_checkpoint.pos
                scene.camera.pos = self.shape.pos = pos * TILE_SIZE
                self.body.position = tuple(pos)
                self.body.velocity = (0.0, 0.0)

            # adjust camera based on self.body.position
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

            delta = pos - last_pos

            screen_pos = pos * TILE_SIZE
            screen_delta = delta * TILE_SIZE

            cwbb = self.cwbb.translate(screen_pos)
            camera = scene.camera.pos

            # print(f"0. {camera=}")

            # move camera
            camera_delta = (screen_delta * 2)
            camera = camera + camera_delta
            # print(f"   translate camera by {camera_delta=}")

            # print(f"1. {screen_pos=}")
            # print(f"   {cwbb=}")
            # print(f"   {camera=}")
            if not cwbb.contains(camera):
                x, y = camera
                if x < cwbb.l:
                    x = cwbb.l
                elif x > cwbb.r:
                    x = cwbb.r
                if y < cwbb.b:
                    y = cwbb.b
                elif y > cwbb.t:
                    y = cwbb.t
                camera = vec2(x, y)
                # print(f"   adjusted to {camera}")

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

            last_pos = pos




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
