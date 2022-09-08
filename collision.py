#!/usr/bin/env python3

##
## collision.py
## Copyright 2022 by Larry Hastings
##
## Collision logic for 2D platformer games.
##
## Terminology:
##    A "grid" is the entire area we do collision for.
##    A "cell" is an individual square on the grid.  Cells can contain tiles.
##    A "tile" is an object placed on the grid, *in* a particular cell.
##    A "pawn" is a movable object that doesn't live in the grid.  You ask
##       the grid "is this pawn colliding with anything?"
##
##    Cells, tiles, and pawns are all *at* a particular set of coordinates,
##    but tiles are *in* cells, and cells are *in* the grid.
##
##    Cells and tiles are always 1 unit wide and 1 unit tall.
##    Pawns can be any width or height, but their size is expressed in cell units.
##
## When you ask about collision information, you're asking the "grid"
## if this "pawn" is colliding with anything.  If it is, the grid will
## give you a list of "tiles" that it's colliding with.  Depending on the
## size of the pawn,
##
## In GridCollider's opinion:
##    if a pawn is at location (0, 0),
##    and it's exactly 1 tile wide and 1 tile tall,
##    it does *not* collide with tiles in cells at
##      (0, 1), (1, 0), or (1, 1).
##
from collections import defaultdict
from math import ceil, floor, inf, modf, nextafter
from wasabigeom import vec2
from typing import Protocol, TypeVar, Generic, Union, Optional, Sequence, overload


vec2_zero = vec2(0, 0)
vec2_0_1  = vec2(0, 1)
vec2_1_0  = vec2(1, 0)
vec2_1_1  = vec2(1, 1)

Number = Union[float, int]
Vec2Like = Union[vec2, tuple[Number, Number]]


class AbstractTile(Protocol):
    pos: Vec2Like


class AbstractPawn(Protocol):
    """Things that can move within the collider."""

    size: vec2


class AbstractPositionedPawn(Protocol):
    """A thing that can move within the collider, with its own position."""

    size: vec2
    pos: Vec2Like


T = TypeVar('T', bound=AbstractTile)


class GridCollider(Generic[T]):
    def __init__(self, size: Vec2Like):
        size = vec2(size)
        self.size = size
        self.grid: defaultdict[vec2, tuple[T, ...]] = defaultdict(tuple)
        self.tiles_seen = set()

    def add(self, tile: T) -> None:
        if tile in self.tiles_seen:
            raise ValueError(f"tile {tile} already in grid")
        pos = vec2(tile.pos)
        if (pos.x > self.size.x) or (pos.y > self.size.y):
            raise ValueError(f"tile {tile} is outside the grid, grid is size ({self.size.x}, {self.size.y})")
        value = self.grid[pos]
        self.grid[pos] = value + (tile,)

    def remove(self, tile: T) -> None:
        """
        Removes tile from the grid.

        If the tile is not on the grid
        (at that position), does nothing.
        """
        if tile not in self.tiles_seen:
            raise ValueError(f"tile {tile} not in grid")
        pos = vec2(tile.pos)
        value = self.grid[pos]
        index = value.index(tile)
        new_value = value[0:index] + value[index + 1:-1]
        assert tile not in new_value
        self.grid[pos] = new_value

    def __contains__(self, tile: T) -> bool:
        result = tile in self.tiles_seen
        # a little double-checking, only slows it down a little
        pos = vec2(tile.pos)
        result2 = tile in self.grid[pos]
        assert result == result2
        return result

    @overload
    def collide_pawn(self, pawn: AbstractPositionedPawn) -> Optional[Sequence[T]]:
        ...

    @overload
    def collide_pawn(self, pawn: AbstractPawn, pos: Vec2Like) -> Optional[Sequence[T]]:
        ...

    def collide_pawn(
        self,
        pawn,
        pos: Optional[Vec2Like] = None
    ) -> Optional[Sequence[T]]:
        """
        Queries the grid to see if the pawn collides with any tiles.

        pawn has to have .size, a vec2().
        If you don't pass in an explicit pos,
        pawn has to have a .pos, a vec2().

        returns None if there are no collisions.
        returns an iterable of tiles if there are collisions.
        """
        if pos is None:
            pos = pawn.pos
        pos = vec2(pos)

        #
        # calling something "aligned" means
        # it's exactly aligned with the grid.
        # it means that the fractional part of your coordinate is zero.
        #   if your position is 18.0, you're aligned.
        #   if your position is 18.anything-but-zero, you're not aligned.
        #
        x_fraction, x_integer = modf(pos.x)
        y_fraction, y_integer = modf(pos.y)
        pos_cell_coord = vec2(x_integer, y_integer)
        x_aligned = 0 if x_fraction else 1
        y_aligned = 0 if y_fraction else 1
        hits = []
        append = hits.append

        if (pawn.size.x <= 1) and (pawn.size.y <= 1) and x_aligned and y_aligned:
            # super-optimized code path
            return self.grid[pos_cell_coord]
        elif (pawn.size.x == 1) and (pawn.size.y == 1):
            # somewhat optimized code path
            tiles = self.grid[pos_cell_coord]
            if tiles:
                append(tiles)
            if not x_aligned:
                tiles = self.grid[pos_cell_coord + vec2_1_0]
                if tiles:
                    append(tiles)
            if not y_aligned:
                tiles = self.grid[pos_cell_coord + vec2_0_1]
                if tiles:
                    append(tiles)
                if not x_aligned:
                    tiles = self.grid[pos_cell_coord + vec2_1_1]
                    if tiles:
                        append(tiles)
        else:
            # non-optimized code path.
            # we need to check an (m x n) grid of tiles.
            for y in range(ceil(pawn.size.y) + (not y_aligned)):
                for x in range(ceil(pawn.size.x) + (not x_aligned)):
                    test_coord = pos_cell_coord + vec2(x, y)
                    tiles = self.grid[test_coord]
                    if tiles:
                        append(tiles)

        if not hits:
            return None
        # this is the fastest way to flatten a list of tuples.
        # (don't bother to turn it into a tuple.)
        return [tile  for hit in hits  for tile in hit]

    @overload
    def collide_moving_pawn(
        self,
        pawn: AbstractPositionedPawn,
        delta: vec2,
    ) -> Optional[tuple[float, vec2, Sequence[T]]]:
        ...

    @overload
    def collide_moving_pawn(
        self,
        pawn: AbstractPawn,
        delta: vec2,
        *,
        pos: Vec2Like
    ) -> Optional[tuple[float, vec2, Sequence[T]]]:
        ...

    def collide_moving_pawn(
        self,
        pawn,
        delta: vec2,
        *,
        pos: Optional[Vec2Like] = None
    ) -> Optional[tuple[float, vec2, Sequence[T]]]:
        """
        Queries the grid to see if a moving pawn collides with any tiles.

        pawn has to have .size, a vec2().
        If you don't pass in an explicit pos,
        pawn has to have a .pos, a vec2().
        delta must be a vec2(), which is added to pawn to produce its final coordinate.

        if there are no collisions, returns None.

        if there are collisions, return value is
            (t, pos, hits)
        where
          t is a number in the range [0, 1]
            indicating the time at which the collision occured
          pos is the position the pawn was at at time t
          hits is the same return value as from collision().
        """
        assert isinstance(delta, vec2)
        if pos is None:
            pos = pawn.pos
        pos = vec2(pos)

        # print(f"collide_moving_pawn: {pawn=} {delta=} {pos=}")

        # First, test to see if we're colliding at time t=0.
        # If we're already colliding, we're done.
        hits = self.collide_pawn(pawn, pos)
        if hits:
            # print(f"    found at time t=0: {hits}")
            yield (0, pos, hits)
            return

        # Okay, we have to do the hard thing.  Here's how it works.
        #
        # Since we weren't colliding at time t=0, any collision that does
        # happen will only happen as the pawn moves.
        #
        # If our pawn is moving up and to the right:
        #
        #    end
        #    pos-> +--+
        #         /| /|
        # start  / |/_|  _
        # pos-> +--+ /   /|
        #       |  |/   /   <-delta (vector)
        #       +--+   /
        #
        # then, since it wasn't colliding at time t=0,
        # any new collision will only happen as a result of
        # it moving into a new cell on the grid, which can only
        # happen on the leading edges.  In this case it would be
        # the top and right edges.  (If the pawn were moving
        # down and left, it would be the left and bottom edges.
        # And if the pawn were only moving right, it would be
        # only the right edge.)
        #
        # So, from a high level, what we do is:
        #   For each direction x and y that the pawn is moving in,
        #     we find the corresponding x or y coordinate of the appropriate leading edge.
        #     We then calculate the time t at which that coordinate enters a new cell.
        #     Then we calculate collision based on moving pawn to that time t
        #         pos = (delta * t)
        #     If there are collisions, store (t, pos, collisions) in a list and break.
        #     Else, if we reach a time t > 1.0, break.
        #
        # If the list is empty, the pawn never hit anything.
        # if the list is not empty, sort it lowest first and return list[0].

        x_aligned = 0 if modf(pos.x)[0] else 1
        y_aligned = 0 if modf(pos.y)[0] else 1

        size = vec2(pawn.size)
        size_x_aligned = 0 if modf(size.x)[0] else 1
        size_y_aligned = 0 if modf(size.y)[0] else 1

        top_right = pos + size

        candidates = []

        def check_moving_pawn_along_one_coordinate(start, scalar_delta):
            assert scalar_delta
            if scalar_delta > 0:
                sign = 1
                towards = inf
            else:
                sign = -1
                towards = -inf
            # how far do we have to move initially to push this edge to border on its first new cell?
            fractional, integer = modf(start)
            edge_aligned = 0 if fractional else 1
            if edge_aligned:
                coord = start
            else:
                coord = integer + sign

            # print(f"  check_moving_pawn_along_one_coordinate: {start=} {scalar_delta=}")

            while True:
                # print(f"      --")

                # now scootch it just a teensy bit further, so we're intruding into that cell
                next_coord = nextafter(coord, towards)

                # find the lowest time t such that
                #     start + (scalar_delta * t) >= next_coord
                t = (next_coord - start) / scalar_delta
                if t > 1:
                    break

                # make sure it's properly reversible
                coord_at_time_t = start + (scalar_delta * t)

                # print(f"      {coord=} {next_coord=} {t=} {coord_at_time_t=}")

                assert coord_at_time_t >= next_coord

                new_pos = pos + (delta * t)
                hits = self.collide_pawn(pawn, pos=new_pos)
                # print(f"      {delta=} {new_pos=} {pos + size + (delta * t)=} {hits=}")
                if hits:
                    # print("found! {(t, new_pos, hits)=}")
                    yield (t, new_pos, hits)

                coord += sign

        iterators = []
        if delta.x > 0:
            # moving right, check right edge
            x_iterator = check_moving_pawn_along_one_coordinate(top_right.x, delta.x)
        elif delta.x < 0:
            # moving left, check left edge
            x_iterator = check_moving_pawn_along_one_coordinate(pos.x, delta.x)
        else:
            x_iterator = None

        if delta.y > 0:
            # moving up, check top edge
            y_iterator = check_moving_pawn_along_one_coordinate(top_right.y, delta.y)
        elif delta.y < 0:
            # moving down, check bottom edge
            y_iterator = check_moving_pawn_along_one_coordinate(pos.y, delta.y)
        else:
            y_iterator = None

        if not (x_iterator or y_iterator):
            return

        x = None
        y = None
        previous = None
        while True:
            if x is None:
                try:
                    x = next(x_iterator)
                except StopIteration:
                    pass

            if y is None:
                try:
                    y = next(y_iterator)
                except StopIteration:
                    if x is None:
                        return

            # print(f"loop:\n  {x=}\n\n  {y=}\n\n  {x and y=}\n")
            if bool(x) and bool(y):
                if x[0] == y[0]:
                    # combine
                    assert x[1] == y[1]
                    all_hits = tuple(set(x[2]) | set(y[2]))
                    value = (x[0], x[1], all_hits)
                    x = None
                    y = None
                elif x[0] < y[0]:
                    value = x
                    x = None
                else:
                    value = y
                    y = None
            elif x:
                value = x
                x = None
            else:
                assert y
                value = y
                y = None

            # cull redundant results
            should_yield = not previous
            if not should_yield:
                previous_hits = set(previous[2])
                value_hits = set(value[2])
                should_yield = value_hits != previous_hits
            if should_yield:
                yield value
                previous = value


if __name__ == "__main__":
    # simple test suite
    import sys

    pawn_next_id = 1
    class Pawn:
        def __init__(self, pos, size):
            global pawn_next_id
            self.id = pawn_next_id
            pawn_next_id += 1
            self.pos = pos
            self.size = size

        def __repr__(self):
            return f"<Pawn {self.id:02} pos={self.pos} size={self.size}>"

    tile_next_id = 1
    class Tile:
        def __init__(self, pos):
            global tile_next_id
            self.id = tile_next_id
            tile_next_id += 1
            self.pos = pos

        def __repr__(self):
            return f"<Tile {self.id:02} pos={self.pos}>"

    local_tests_run = 0
    global_tests_run = 0

    failure_text = []

    class raw_string:
        def __init__(self, s):
            self.s = s
        def __repr__(self):
            return self.s
        def __str__(self):
            return self.s

    def make_hits_pretty(hits):
        if not hits:
            return str(hits)
        hits = list(hits)
        hits.sort(key=lambda tile: tile.id)
        hits = [raw_string(f"{tile_names[tile]}") for tile in hits]
        return hits

    def make_result_tuple_pretty(t):
        if not t:
            return "None"
        hits = make_hits_pretty(t[2])
        return (t[0], t[1], hits)

    def failure_print(*a):
        failure_text.append("".join(str(o) for o in a))

    def failure_exit():
        sys.exit("\n".join(failure_text))

    def failure_clear():
        failure_text.clear()

    def test_collide_pawn(pawn, expected, *, pos=None):
        global local_tests_run
        local_tests_run += 1
        global global_tests_run
        global_tests_run += 1

        got = grid.collide_pawn(pawn, pos=pos)

        if (got == None) and (expected == None):
            return

        got_set = set(got) if got else set()
        expected_set = set(expected) if expected else set()
        if got_set == expected_set:
            return

        failure_print()
        failure_print(f"Failure in test_collide_pawn test {local_tests_run}:")
        failure_print(f"        pawn: {pawn}")
        failure_print(f"    expected: {expected}")
        failure_print(f"         got: {make_hits_pretty(got)}")
        failure_exit()


    grid: GridCollider[Tile] = GridCollider(vec2(200, 100))

    tile_names = {}

    tile_15_20 = Tile(vec2(15, 20))
    grid.add(tile_15_20)
    tile_names[tile_15_20] = "tile_15_20"

    tile_16_20 = Tile(vec2(16, 20))
    grid.add(tile_16_20)
    tile_names[tile_16_20] = "tile_16_20"

    tile_17_20 = Tile(vec2(17, 20))
    grid.add(tile_17_20)
    tile_names[tile_17_20] = "tile_17_20"

    tile_15_21 = Tile(vec2(15, 21))
    grid.add(tile_15_21)
    tile_names[tile_15_21] = "tile_15_21"

    tile_16_21 = Tile(vec2(16, 21))
    grid.add(tile_16_21)
    tile_names[tile_16_21] = "tile_16_21"

    tile_17_21 = Tile(vec2(17, 21))
    grid.add(tile_17_21)
    tile_names[tile_17_21] = "tile_17_21"


    vec2_1_1 = vec2(1, 1)
    vec2_2_2 = vec2(2, 2)
    vec2_3_3 = vec2(3, 3)

    pawn = Pawn(vec2(10, 10), vec2_1_1)

    test_collide_pawn(pawn, ())

    pawn.pos = tile_15_20.pos
    test_collide_pawn(pawn, (tile_15_20,))

    try:
        pawn.pos = tile_15_20.pos
        test_collide_pawn(pawn, (tile_15_20,tile_16_20))
    except SystemExit:
        failure_clear()

    pawn.pos = vec2(tile_15_20.pos.x - 0.2, tile_15_20.pos.y - 0.2)
    test_collide_pawn(pawn, (tile_15_20,))

    pawn.pos = tile_16_20.pos
    test_collide_pawn(pawn, (tile_16_20,))

    pawn.pos = tile_15_20.pos
    pawn.size= vec2_2_2
    test_collide_pawn(pawn, (tile_15_20, tile_16_20, tile_15_21, tile_16_21))

    pawn.pos = vec2(tile_15_20.pos.x - 1, tile_15_20.pos.y)
    pawn.size= vec2_2_2
    test_collide_pawn(pawn, (tile_15_20, tile_15_21))

    pawn.pos = vec2(tile_15_20.pos.x, tile_15_20.pos.y - 1)
    pawn.size= vec2_2_2
    test_collide_pawn(pawn, (tile_15_20, tile_16_20))

    pawn.pos = vec2(tile_15_20.pos.x - 0.4, tile_15_20.pos.y - 0.4)
    pawn.size= vec2_2_2
    test_collide_pawn(pawn, (tile_15_20, tile_16_20, tile_15_21, tile_16_21))

    pawn.pos = vec2(15.5, 21.1)
    pawn.size= vec2_3_3
    test_collide_pawn(pawn, (tile_15_21, tile_16_21, tile_17_21))

    pawn.pos = vec2(15.1, 20.1)
    delta = vec2(3, 3)
    pawn.size = vec2_1_1
    test_collide_pawn(pawn, ({tile_15_20, tile_15_21, tile_16_20, tile_16_21}))


    local_tests_run = 0

    def test_collide_moving_pawn_first_result(pawn, delta, expected, *, pos=None):
        global local_tests_run
        local_tests_run += 1
        global global_tests_run
        global_tests_run += 1

        values = [x for x in grid.collide_moving_pawn(pawn, delta, pos=pos)]
        if not values:
            got = None
        else:
            got = values[0]

        if (expected is None) and (got == None):
            return

        expected_triple = expected or (None, None, ())
        expected_t, expected_pos, expected_hits = expected_triple

        got_triple = got or (None, None, ())
        got_t, got_pos, got_hits = got_triple

        if (got_t == expected_t) and (got_pos == expected_pos) and (set(got_hits) == set(expected_hits)):
            return

        failure_print(f"Failure in test_collide_moving_pawn_first_result test {local_tests_run}:")
        failure_print(f"        pawn: {pawn}")
        failure_print(f"       delta: {delta}")
        failure_print(f"    expected: {expected}")
        failure_print(f"         got: {make_hits_pretty(got)}")
        failure_exit()

    pawn.pos = vec2(14, 19)
    delta = vec2(2, 2)
    pawn.size = vec2_1_1
    test_collide_moving_pawn_first_result(pawn, delta,
        (1.7763568394002505e-15, vec2(14.000000000000004, 19.000000000000004), [tile_15_20])
        )

    pawn.pos = vec2(13, 20)
    delta = vec2(3, 0.5)
    test_collide_moving_pawn_first_result(pawn, delta,
        (0.3333333333333339, vec2(14.000000000000002, 20.166666666666668), [tile_15_20, tile_15_21])
        )

    pawn.pos = vec2(15, 23)
    pawn.size = vec2_3_3
    delta = vec2(1, -2)
    test_collide_moving_pawn_first_result(pawn, delta,
        (0.5000000000000018, vec2(15.500000000000002, 21.999999999999996), [tile_15_21, tile_16_21, tile_17_21])
        )

    local_tests_run = 0
    def test_collide_moving_pawn_all_results(pawn, delta, expected, *, pos=None):
        global local_tests_run
        local_tests_run += 1
        global global_tests_run
        global_tests_run += 1

        got = [(x[0], x[1], set(x[2])) for x in grid.collide_moving_pawn(pawn, delta, pos=pos)]
        expected = [(x[0], x[1], set(x[2])) for x in expected]

        if got == expected:
            return

        failure_print(f"Failure in test_collide_moving_pawn_all_results test {local_tests_run}:")
        failure_print(f"        pawn: {pawn}")
        failure_print(f"       delta: {delta}")
        failure_print(f"    expected: {expected}")
        failure_print(f"         got:")
        failure_print(f"              [")
        for o in got:
            failure_print(f"              ", make_result_tuple_pretty(o))
        failure_print(f"              ]")
        failure_exit()

    pawn.pos = vec2(14, 19)
    delta = vec2(3, 3)
    pawn.size = vec2_1_1
    test_collide_moving_pawn_all_results(pawn, delta,
        [
        (1.1842378929335002e-15, vec2(14.000000000000004, 19.000000000000004), [tile_15_20]),
        (0.33333333333333454, vec2(15.000000000000004, 20.000000000000004), [tile_15_20, tile_16_20, tile_15_21, tile_16_21]),
        (0.6666666666666679, vec2(16.000000000000004, 21.000000000000004), [tile_16_21, tile_17_21]),
        ]
        )



    print(f"All {global_tests_run} tests passed.")

