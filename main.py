import bisect
import collections
import math
import pygame

import wasabi2d.loop
from wasabi2d.clock import Clock
import wasabi2d as w2d
import wasabigeom

vec2 = wasabigeom.vec2

hud_layer = 0
sprite_layer = 1
landscape_layer = 2

layers = list(range(3))


scene = w2d.Scene()
scene.background = (0.9, 0.9, 0.9)

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


tile_map = scene.layers[landscape_layer].add_tile_map()
block_tile = 'red_block_20x20'


class Block:
    def __init__(self, x, y=None):
        if (y is None) and isinstance(x, vec2):
            position = x
        else:
            position = vec2(x, y)
        self.pos = position
        grid[int(position.x)][int(position.y)].append(self)

        # self.shape = scene.layers[0].add_rect(cell_size, cell_size, fill=True, color='red', pos=(position.x*cell_size, position.y*cell_size))
        tile_map[x, y] = block_tile


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


actions = {
    "up",
    "down",
    "left",
    "right",
    "jump,"
    "shoot",
    "pause",
    "quit",
}



main_clock = Clock()
game_clock = main_clock.create_sub_clock()


player_max_jumps = 2
player_max_dashes = 1


class Player:
    def __init__(self):
        self.shape = None
        self._pos = None
        self.actions = collections.defaultdict(int)
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

        self.jumps = player_max_jumps
        self.dashes = player_max_dashes

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, v):
        self._pos = v
        if self.shape:  # FIXME: don't make this class stateful
            self.shape.pos = v * cell_size

    def refresh_state(self):
        for name, value in self.actions.items():
            assert value >= 0, f"actions[{name!r}] is {value}, which is < 0!"

        self.desired_x_speed = ((self.actions['right'] and 1) + (self.actions['left'] and -1)) * self.maximum_x_speed
        if self.speed.x != self.desired_x_speed:
            self.x_acceleration = self.x_acceleration_factor
            if self.speed.x > self.desired_x_speed:
                self.x_acceleration = -self.x_acceleration

        y_speed = self.speed.y

        if self.actions['jump'] and self.jumps:
            # print("jump!")
            self.jumps -= 1
            y_speed = self.jump_y_speed

        self.speed = vec2(self.speed.x, y_speed)
        # print(f"{self.pos=} {self.speed=}")

    async def handle_keys(self):
        key_to_action = {
            w2d.keys.W: 'up',
            w2d.keys.A: 'left',
            w2d.keys.S: 'down',
            w2d.keys.D: 'right',

            w2d.keys.SPACE: 'jump',
            w2d.keys.RETURN: 'shoot',
        }
        async for ev in w2d.events.subscribe(pygame.KEYDOWN, pygame.KEYUP):
            key = w2d.constants.keys(ev.key)
            if not (action := key_to_action.get(key)):
                continue
            if ev.type == pygame.KEYDOWN:
                self.actions[action] += 1
                self.refresh_state()
            else:
                self.actions[action] -= 1
                self.refresh_state()

    async def run(self):
        self.shape = scene.layers[sprite_layer].add_star(points=6, outer_radius=cell_size, inner_radius=cell_size / 2, fill=True, color=(0.5, 0.5, 0.5))
        with self.shape:
            async with w2d.Nursery() as ns:
                ns.do(self.run_physics())
                ns.do(self.handle_keys())

    async def run_physics(self):
        async for _ in game_clock.coro.frames():
            self.on_tick()

    def on_tick(self):
        dt = 1/60

        # print(f"update: {t=} {dt=}")
        # print(f"    start {self.pos=} {self.speed=}")
        starting_pos = self.pos
        starting_cell_x = int(self.pos.x)
        starting_cell_y = int(self.pos.y)

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
                    if isinstance(cell, Block):
                        collision = True
                        break
                else:
                    collision = False

                if collision:
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


for x in range(10, 14):
    Block(x, 20)

for x in range(15, 19):
    Block(x, 20)

for x in range(21, 28):
    Block(x, 16)


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


async def main():
    player = Player()
    player.pos = current_checkpoint.pos

    async with w2d.Nursery() as ns:
        ns.do(drive_main_clock())
        ns.do(pauser())
        ns.do(player.run())


w2d.run(main())
