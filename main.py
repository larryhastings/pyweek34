import bisect
import collections
import math

import wasabi2d.loop
from wasabi2d.clock import Clock
import wasabi2d as w2d
import wasabigeom
vec2 = wasabigeom.vec2

import pygame

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



main_clock = Clock()
game_clock = main_clock.create_sub_clock()

class Game:
    pass

class Level:
    def __init__(self):
        self.color_state = {color: True for color in colors}

    def toggle_color(self, color):
        new_state = not self.color_state[color]
        self.color_state[color] = new_state
        scene.layers[color_to_layer[color]].visible = new_state



player_max_jumps = 2
player_max_dashes = 1


class Player:
    def __init__(self):
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

        self.jumps = player_max_jumps
        self.dashes = player_max_dashes

        self.stateful_actions = {
            'move_up': 0,
            'move_left': 0,
            'move_down': 0,
            'move_right': 0,
            }
        self.momentary_actions_queue = collections.deque()

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, v):
        self._pos = v
        if self.shape:
            self.shape.pos = v * cell_size

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
            print(f"{action=} {ev=}")
            print()
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


async def main():
    global game
    global level
    global player
    game = Game()
    level = Level()
    player = Player()
    player.pos = current_checkpoint.pos

    async with w2d.Nursery() as ns:
        ns.do(drive_main_clock())
        ns.do(pauser())
        ns.do(player.run())


w2d.run(main())
