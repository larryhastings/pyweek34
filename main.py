import bisect
import collections
from contextlib import contextmanager
from typing import Any, Generator
import typing

import pymunk
import wasabi2d.loop
from wasabi2d.clock import Clock
import wasabi2d as w2d
from wasabigeom import vec2

import pygame


TILE_SIZE: int = 20
FRICTION: float = 0
GRAVITY: float = 20

colors = {'red', 'orange', 'yellow', 'green', 'blue', 'purple'}

layers = list(range(8))
hud_layer, sprite_layer, red_layer, orange_layer, yellow_layer, green_layer, blue_layer, purple_layer = layers

color_to_layer = {
    'red': red_layer,
    'orange': orange_layer,
    'yellow': yellow_layer,
    'green': green_layer,
    'blue': blue_layer,
    'purple': purple_layer,
}


scene = w2d.Scene()
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
    size: tuple[int, int] = (1, 1)
) -> None:
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
    poly.friction = FRICTION
    poly.elasticity = 0
    space.add(poly)


class Positionable(typing.Protocol):
    pos: vec2


_physical_objects: dict[pymunk.Body: Positionable] = {}


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
            _physical_objects[body] = drawn
            yield body
    finally:
        space.remove(body, *body.shapes)
        del _physical_objects[body]


# expressed in cells
scene_width = 80
scene_height = 40

cell_size = 20

# cell = grid[x][y]
# isinstance(cell, list)
grid = []

for _ in range(scene_width + 1):
    row = []
    grid.append(row)
    for __ in range(scene_height + 1):
        row.append([])


color_tile_maps = {}
for color, layer in color_to_layer.items():
    color_tile_maps[color] = scene.layers[layer].add_tile_map()


colored_block_tiles = {
    'red': 'red_block_20x20',
    'blue': 'blue_block_20x20',
}


class Block:
    def __init__(self, color, x, y=None):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        grid[int(position.x)][int(position.y)].append(self)
        assert color in colored_block_tiles
        self.color = color

        # self.shape = scene.layers[0].add_rect(cell_size, cell_size, fill=True, color='red', pos=(position.x*cell_size, position.y*cell_size))
        tile_map = color_tile_maps[color]
        tile_map[x, y] = colored_block_tiles[color]

        self.shape = create_static(position)

    def is_solid(self):
        return level.color_state[self.color]


current_checkpoint = None


class Checkpoint:
    def __init__(self, x, y=None, *, initial=False):
        global current_checkpoint
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        grid[int(position.x)][int(position.y)].append(self)
        if initial:
            current_checkpoint = self


ACTIONS = {
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



main_clock = Clock()
game_clock = main_clock.create_sub_clock()


class Level:
    def __init__(self):
        self.color_state = {color: True for color in colors}

    def toggle_color(self, color):
        new_state = not self.color_state[color]
        self.color_state[color] = new_state
        scene.layers[color_to_layer[color]].visible = new_state



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
        self._pos = None
        self.speed = vec2(0, 0)
        self.x_acceleration = 0
        self.desired_x_speed = 0

        self.death_plane = scene_height

        # TODO
        # these are tuned to feel good.
        # more tuning is probably required.
        # in particular, we should tune jumps so they
        # reliably achieve Y tiles vertically,
        # and if you're moving at full speed you
        # reliably clear an X tile gap horizontally.
        #
        self.maximum_x_speed = 40 # cells per second
        self.x_acceleration_factor = 400 # cells per second per second
        self.jump_y_speed = -70 # cells per second
        self.gravity = 400 # cells per second per second
        self.terminal_velocity = 100 # cells per second
        self.maximum_y = 19

        self.controller = Controller()
        self._standing_on_count = 0
        self.on_ground = w2d.Event()

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, v):
        self._pos = v
        if self.shape:
            self.shape.pos = v * cell_size

    def _add_floor(self):
        self._standing_on_count += 1
        self.on_ground.set()

    def _remove_floor(self):
        self._standing_on_count -= 1
        if self._standing_on_count == 0:
            self.on_ground = w2d.Event()

    def refresh_state(self):
        for name, value in self.stateful_actions.items():
            assert value >= 0, f"actions[{name!r}] is {value}, which is < 0!"

        self.desired_x_speed = ((self.stateful_actions['move_right'] and 1) + (self.stateful_actions['move_left'] and -1)) * self.maximum_x_speed
        if self.speed.x != self.desired_x_speed:
            self.x_acceleration = self.x_acceleration_factor
            if self.speed.x > self.desired_x_speed:
                self.x_acceleration = -self.x_acceleration

        y_speed = self.speed.y

        for action in self.momentary_actions_queue:
            if action == 'jump' and self.jumps:
                # print("jump!")
                self.jumps -= 1
                y_speed = self.jump_y_speed
            if action.startswith('toggle_'):
                color = action.partition('_')[2]
                level.toggle_color(color)

        self.momentary_actions_queue.clear()

        self.speed = vec2(self.speed.x, y_speed)
        # print(f"{self.pos=} {self.speed=}")

    async def handle_keys(self):
        key_to_action = {
            w2d.keys.W: 'move_up',
            w2d.keys.A: 'move_left',
            w2d.keys.S: 'move_down',
            w2d.keys.D: 'move_right',

            w2d.keys.UP: 'move_up',
            w2d.keys.DOWN: 'move_left',
            w2d.keys.LEFT: 'move_down',
            w2d.keys.RIGHT: 'move_right',

            w2d.keys.SPACE: 'jump',
            w2d.keys.RETURN: 'shoot',

            w2d.keys.K_1: "toggle_red",
            w2d.keys.K_2: "toggle_orange",
            w2d.keys.K_3: "toggle_yellow",
            w2d.keys.K_4: "toggle_green",
            w2d.keys.K_5: "toggle_blue",
            w2d.keys.K_6: "toggle_purple",
        }
        async for ev in w2d.events.subscribe(pygame.KEYDOWN, pygame.KEYUP):
            key = w2d.constants.keys(ev.key)
            if not (action := key_to_action.get(key)):
                continue
            if ev.type == pygame.KEYDOWN:
                if action in self.stateful_actions:
                    print("state +", action, ev)
                    self.stateful_actions[action] += 1
                else:
                    self.momentary_actions_queue.append(action)
            else:
                if action in self.stateful_actions:
                    self.stateful_actions[action] -= 1
            self.refresh_state()

    async def run(self, start_pos: vec2):
        self.shape = scene.layers[sprite_layer].add_star(
            pos=start_pos * TILE_SIZE,
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
                #ns.do(self.handle_keys())

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
                ns.do(_jump_on_press())
                await self.on_ground
                ns.cancel()

    def on_tick(self):
        dt = 1/60

        speed_x, speed_y = self.speed
        starting_speed_x = speed_x
        starting_speed_y = speed_y
        if speed_x != self.desired_x_speed:
            before = speed_x < self.desired_x_speed
            speed_x += self.x_acceleration * dt
            after = speed_x < self.desired_x_speed
            if before != after:
                speed_x = self.desired_x_speed

        speed_y += self.gravity * dt
        if speed_y > self.terminal_velocity:
            speed_y = self.terminal_velocity
        # print(f"    speed_y changed by {self.gravity * dt}, is now {speed_y}")

        if ((speed_x != starting_speed_x) or (speed_y != starting_speed_y)):
            self.speed = vec2(speed_x, speed_y)

        delta = self.speed * dt

        # death plane
        if (self.pos.y + delta.y) >= self.death_plane:
            self.pos = current_checkpoint.pos
            self.speed = vec2(0, 0)
            delta = 0
        else:
            # lame second approximation for collision.
            # instead of moving the character by "delta"
            # all at once, move using a number of steps,
            # at least two.
            steps = int(max(delta.x, delta.y, 1) * 2)

            new_pos = self.pos
            delta_per_step = delta / steps
            for _ in range(steps):
                new_pos += delta_per_step

                # lame first approximation for collision.
                # if we end the tick sticking into a block,
                # simply move the player up until they're
                # resting on the block.

                final_cell_x = int(new_pos.x)
                final_cell_y = int(new_pos.y)
                cell_below_y = final_cell_y + 1
                cells = grid[final_cell_x][cell_below_y]

                for cell in cells:
                    if isinstance(cell, Block) and cell.is_solid():
                        collision_below = True
                        break
                else:
                    collision_below = False

                if collision_below:
                    self.jumps = player_max_jumps
                    delta_per_step = vec2(delta_per_step.x, 0)
                    self.speed = vec2(self.speed.x, 0)
                    new_pos = vec2(new_pos.x, final_cell_y)
            self.pos = new_pos


async def drive_main_clock():
    # convert time into ticks.
    # there are 60 ticks in a second.
    # the basic idea:
    #    whenever wasabi calls us,
    #    we compare the last time to the current
    #    time.  for every 1/60s threshold that has
    #    elapsed since last time, send a tick to
    #    all clocks.
    tick_offsets = [(i+1)/60 for i in range(60)]

    next_tick_seconds = None
    next_tick_fractional = None
    next_tick_index = None

    # if we fall behind more than this many ticks,
    # just send in this many ticks and continue.
    max_ticks = 6

    next_tick_seconds, fractional = 0, 0
    next_tick_index = bisect.bisect(tick_offsets, fractional)
    next_tick_fractional = tick_offsets[next_tick_index]

    async for t in wasabi2d.clock.coro.frames():
        assert t >= next_tick_seconds
        fractional = t - next_tick_seconds
        assert fractional <= (62/60)
        ticks = 0
        while fractional >= next_tick_fractional:
            ticks += 1

            next_tick_index += 1
            if next_tick_index == 60:
                assert next_tick_fractional == 1
                next_tick_index = 0
                fractional -= 1
                next_tick_seconds += 1
            next_tick_fractional = tick_offsets[next_tick_index]

        ticks = min(ticks, max_ticks)
        for _ in range(ticks):
            main_clock.tick(1 / 60)


def init_level():
    for x in range(10, 14):
        Block('red', x, 20)

    for x in range(15, 19):
        Block('red', x, 20)

    for x in range(21, 28):
        Block('blue', x, 16)

    Checkpoint(11, 18, initial=True)


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


async def run_physics():
    """Step the Pymunk physics simulation."""
    async for dt in game_clock.coro.frames_dt():
        space.step(dt)
        for body, positionable in _physical_objects.items():
            positionable.pos = body.position * TILE_SIZE


async def run_level():
    global level
    global player
    level = Level()
    init_level()
    player = Player(controller=Controller())
    async with w2d.Nursery() as ns:
        ns.do(run_physics())
        ns.do(player.run(start_pos=current_checkpoint.pos))


async def main():
    async with w2d.Nursery() as ns:
        ns.do(drive_main_clock())
        ns.do(pauser())
        ns.do(run_level())


w2d.run(main())
