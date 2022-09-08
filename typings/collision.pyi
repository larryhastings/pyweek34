import abc
from _typeshed import Incomplete
from typing import Optional, Sequence, TypeVar, Union, overload
from wasabigeom import vec2

Number = Union[float, int]
Vec2Like = Union[vec2, tuple[Number, Number]]

class AbstractTile(metaclass=abc.ABCMeta):
    pos: Vec2Like

class AbstractPawn(metaclass=abc.ABCMeta):
    size: vec2

class AbstractPositionedPawn(metaclass=abc.ABCMeta):
    size: vec2
    pos: Vec2Like
T = TypeVar('T', bound=AbstractTile)

class GridCollider:
    size: Incomplete
    grid: Incomplete
    def __init__(self, size: Vec2Like) -> None: ...
    def add(self, tile: T) -> None: ...
    def remove(self, tile: T) -> None: ...
    def __contains__(self, tile: T) -> bool: ...
    @overload
    def collide_pawn(self, pawn: AbstractPositionedPawn) -> Optional[Sequence[T]]: ...
    @overload
    def collide_pawn(self, pawn: AbstractPawn, pos: Vec2Like) -> Optional[Sequence[T]]: ...
    @overload
    def collide_moving_pawn(self, pawn: AbstractPositionedPawn, delta: vec2) -> Optional[tuple[float, vec2, Sequence[T]]]: ...
    @overload
    def collide_moving_pawn(self, pawn: AbstractPawn, delta: vec2, *, pos: Vec2Like) -> Optional[tuple[float, vec2, Sequence[T]]]: ...
