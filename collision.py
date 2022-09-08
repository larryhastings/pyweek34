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

import collections
from math import ceil, floor, inf, modf, nextafter
import wasabigeom
from wasabigeom import vec2

class GridCollider:
    def __init__(self, size):
        size = vec2(size)
        self.size = size
        self.grid = collections.defaultdict(tuple)

    def add(self, tile):
        pos = vec2(tile.pos)
        if (pos.x > self.size.x) or (pos.y > self.size.y):
            raise ValueError(f"tile {tile} is outside the grid, grid is size ({self.size.x}, {self.size.y})")
        value = self.grid[pos]
        if tile in value:
            raise ValueError(f"tile {tile} already in grid at {pos}")
        self.grid[pos] = value + (tile,)

    def remove(self, tile):
        """
        Removes tile from the grid.

        If the tile is not on the grid
        (at that position), does nothing.
        """
        pos = vec2(tile.pos)
        value = self.grid[pos]
        try:
            index = value.index(tile)
        except ValueError:
            raise ValueError(f"tile {tile} not in grid at {pos}")
        new_value = value[0:index] + value[index + 1:-1]
        assert tile not in new_value
        self.grid[pos] = new_value

    def __contains__(self, tile):
        pos = vec2(tile.pos)
        return tile in self.grid[pos]

    def collide_pawn(self, pawn, pos=None):
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
        positions = None
        x_aligned = 0 if modf(pos.x)[0] else 1
        y_aligned = 0 if modf(pos.y)[0] else 1
        if (pawn.size.x <= 1) and (pawn.size.y <= 1) and x_aligned and y_aligned:
            return self.grid[pos]

        # either the pawn is larger than one tile,
        # or it's not axis aligned.
        # either way we need to check an (m x n) grid of tiles.
        pos = vec2(floor(pos.x), floor(pos.y))
        hits = []
        for y in range(ceil(pawn.size.y) + (not y_aligned)):
            for x in range(ceil(pawn.size.x) + (not x_aligned)):
                test = pos + vec2(x, y)
                tiles = self.grid[test]
                if tiles:
                    hits.append(tiles)
        if not hits:
            return None
        # this is the fastest way to flatten a list of tuples.
        # (don't bother to turn it into a tuple.)
        return [tile  for hit in hits  for tile in hit]


    def collide_moving_pawn(self, pawn, delta, *, pos=None):
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
            return (0, pos, hits)

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
                    candidates.append((t, new_pos, hits))
                    # print(f"      found! {candidates[-1]}")
                    break

                coord += sign

        if delta.x > 0:
            # moving right, check right edge
            candidate = check_moving_pawn_along_one_coordinate(top_right.x, delta.x)
        elif delta.x < 0:
            # moving left, check left edge
            candidate = check_moving_pawn_along_one_coordinate(pos.x, delta.x)
        else:
            candidate = None

        if candidate:
            candidates.append(candidate)

        if delta.y > 0:
            # moving up, check top edge
            candidate = check_moving_pawn_along_one_coordinate(top_right.y, delta.y)
        elif delta.y < 0:
            # moving down, check bottom edge
            candidate = check_moving_pawn_along_one_coordinate(pos.y, delta.y)
        else:
            candidate = None

        if candidate:
            candidates.append(candidate)

        if not candidates:
            return None
        candidates.sort()
        return candidates[0]




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

        sys.exit(f"Failure in test_collide_pawn test {local_tests_run}:\n        pawn: {pawn}\n    expected: {expected}\n         got: {got}")


    grid = GridCollider(vec2(200, 100))


    tile_15_20 = Tile(vec2(15, 20))
    grid.add(tile_15_20)

    tile_16_20 = Tile(vec2(16, 20))
    grid.add(tile_16_20)

    tile_17_20 = Tile(vec2(17, 20))
    grid.add(tile_17_20)

    tile_15_21 = Tile(vec2(15, 21))
    grid.add(tile_15_21)

    tile_16_21 = Tile(vec2(16, 21))
    grid.add(tile_16_21)

    tile_17_21 = Tile(vec2(17, 21))
    grid.add(tile_17_21)


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
        pass

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


    local_tests_run = 0

    def test_collide_moving_pawn(pawn, delta, expected, *, pos=None):
        global local_tests_run
        local_tests_run += 1
        global global_tests_run
        global_tests_run += 1

        got = grid.collide_moving_pawn(pawn, delta, pos=pos)

        if (expected is None) and (got == None):
            return

        expected_triple = expected or (None, None, ())
        expected_t, expected_pos, expected_hits = expected_triple

        got_triple = got or (None, None, ())
        got_t, got_pos, got_hits = got_triple

        if (got_t == expected_t) and (got_pos == expected_pos) and (set(got_hits) == set(expected_hits)):
            return

        sys.exit(f"Failure in test_collide_pawn test {local_tests_run}:\n        pawn: {pawn}\n    expected: {expected}\n         got: {got}")

    pawn.pos = vec2(14, 19)
    delta = vec2(2, 2)
    pawn.size = vec2_1_1
    test_collide_moving_pawn(pawn, delta,
        (1.7763568394002505e-15, vec2(14.000000000000004, 19.000000000000004), [tile_15_20])
        )

    pawn.pos = vec2(13, 20)
    delta = vec2(3, 0.5)
    test_collide_moving_pawn(pawn, delta,
        (0.3333333333333339, vec2(14.000000000000002, 20.166666666666668), [tile_15_20, tile_15_21])
        )

    pawn.pos = vec2(15, 23)
    pawn.size = vec2_3_3
    delta = vec2(1, -2)
    test_collide_moving_pawn(pawn, delta,
        (0.5000000000000018, vec2(15.500000000000002, 21.999999999999996), [tile_15_21, tile_16_21, tile_17_21])
        )


    print(f"All {global_tests_run} tests passed.")

