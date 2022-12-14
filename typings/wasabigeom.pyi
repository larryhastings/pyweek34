from typing import Any, ClassVar, Literal, Optional, Union
from typing import overload

namedtuple: function
unit_x: vec2
unit_y: vec2
x_axis: Line
y_axis: Line
zero: vec2


class BasePolygon:
    def find_mtd(self, push_vectors) -> Any: ...
    def get_aabb(self) -> Any: ...
    def intersects(self, other) -> Any: ...
    def project_to_axis(self, axis) -> Any: ...
    def translate(self, v) -> Any: ...
    def __iter__(self) -> Any: ...


class ConvexPolygon(BasePolygon):
    def __init__(self, points) -> None: ...
    def edges(self) -> Any: ...
    def segments(self) -> Any: ...
    def to_tri_strip(self) -> Any: ...


class Line:
    def __init__(self, direction, distance) -> None: ...
    def altitude(self, *args, **kwargs) -> Any: ...
    def distance_to(self, point) -> Any: ...
    @classmethod
    def from_points(cls, *args, **kwargs) -> Any: ...
    def is_inside(self, *args, **kwargs) -> Any: ...
    def is_on_left(self, point) -> Any: ...
    def is_on_right(self, point) -> Any: ...
    def mirror(self, *args, **kwargs) -> Any: ...
    def offset(self) -> Any: ...
    def parallel(self, point) -> Any: ...
    def perpendicular(self, point) -> Any: ...
    def project(self, point) -> Any: ...
    def reflect(self, point) -> Any: ...
    def __neg__(self) -> Any: ...


class LineSegment:
    def __init__(self, line, min_dist, max_dist) -> None: ...
    def _endpoints(self) -> Any: ...
    def distance_to(self, point) -> Any: ...
    def end(self) -> Any: ...
    @classmethod
    def from_points(cls, *args, **kwargs) -> Any: ...
    def length(self) -> Any: ...
    def mid(self) -> Any: ...
    def project(self, point) -> Any: ...
    def start(self) -> Any: ...


class Matrix:
    def __init__(self, *args, **kwargs) -> None: ...
    def identity(self) -> Any: ...
    def rotation(self, doubleangle) -> Any: ...
    def __mul__(self, other) -> Any: ...
    def __reduce__(self) -> Any: ...
    def __rmul__(self, other) -> Any: ...
    def __setstate__(self, state) -> Any: ...

class PolyLine:
    def __init__(self, vertices = ...) -> None: ...
    def segments(self) -> Any: ...
    def __iter__(self) -> Any: ...

class Polygon:
    def __init__(self, vertices = ...) -> None: ...
    def add_contour(self, vertices) -> Any: ...
    def mirror(self, plane) -> Any: ...
    def polylines_facing(self, v, threshold = ...) -> Any: ...

class Projection:
    __slots__: ClassVar[tuple] = ...
    max: Any
    min: Any
    def __init__(self, min, max) -> None: ...
    def intersection(self, other) -> Any: ...

class Rect(BasePolygon):
    @classmethod
    def as_bounding(cls, *args, **kwargs) -> Any: ...
    def bottomleft(self) -> Any: ...
    def bottomright(self) -> Any: ...
    def contains(self, p) -> Any: ...
    @classmethod
    def from_blwh(cls, *args, **kwargs) -> Any: ...
    @classmethod
    def from_cwh(cls, *args, **kwargs) -> Any: ...
    @classmethod
    def from_points(cls, *args, **kwargs) -> Any: ...
    def get_aabb(self) -> Any: ...
    def intersection(self, r) -> Any: ...
    def overlaps(self, r) -> Any: ...
    def topleft(self) -> Any: ...
    def topright(self) -> Any: ...
    def translate(self, off) -> Any: ...
    @property
    def edges(self) -> Any: ...
    @property
    def h(self) -> Any: ...
    @property
    def points(self) -> Any: ...
    @property
    def w(self) -> Any: ...

class Segment:
    def __init__(self, p1, p2) -> None: ...
    def intersects(self, other) -> Any: ...
    def project_to_axis(self, axis) -> Any: ...
    def scale_to(self, dist) -> Any: ...
    def truncate(self, *args, **kwargs) -> Any: ...
    @property
    def length(self) -> Any: ...

class SpatialHash:
    def __init__(self, cell_size = ...) -> None: ...
    def _add(self, cell_coord, o) -> Any: ...
    def _cells_for_rect(self, r: Rect) -> Any: ...
    def _remove(self, cell_coord, o) -> Any: ...
    def add_rect(self, r, obj) -> Any: ...
    def potential_intersection(self, r) -> Any: ...
    def remove_rect(self, r, obj) -> Any: ...

class Transform:
    def __init__(self, *args, **kwargs) -> None: ...
    def __pyx_fuse_0transform(self, *args, **kwargs) -> Any: ...
    def __pyx_fuse_1transform(self, *args, **kwargs) -> Any: ...
    def build(self, xlate = ..., doublerot = ..., scale = ...) -> Any: ...
    def factorise(self) -> Any: ...
    def identity(self) -> Any: ...
    def inverse(self) -> Any: ...
    def set(self, xlate = ..., doublerot = ..., scale = ...) -> Any: ...
    def transform(self, signatures, args, kwargs, defaults) -> Any: ...
    def __mul__(self, other) -> Any: ...
    def __reduce__(self) -> Any: ...
    def __rmul__(self, other) -> Any: ...
    def __setstate__(self, state) -> Any: ...

class Triangle:
    def __init__(self, base, primary, secondary) -> None: ...
    def area(self) -> Any: ...
    def first(self) -> Any: ...
    @classmethod
    def from_points(cls, *args, **kwargs) -> Any: ...
    def is_clockwise(self) -> Any: ...
    def second(self) -> Any: ...


Number = Union[float, int]
Vec2Like = Union[vec2, tuple[Number, Number]]


class vec2:
    x: float
    y: float

    @overload
    def __init__(self, v: Vec2Like, /) -> None: ...

    @overload
    def __init__(self, x: Number, y: Number, /) -> None: ...

    def angle(self) -> float: ...
    def angle_to(self, other: Vec2Like) -> float: ...
    def cross(self, other: Vec2Like) -> float: ...
    def distance_to(self, other) -> float: ...
    def dot(self, other) -> float: ...

    @staticmethod
    def from_polar(self, length: Number, angle: Number) -> vec2: ...

    def is_zero(self) -> bool: ...
    def length(self) -> float: ...
    def length_squared(self) -> float: ...
    def normalized(self) -> vec2: ...
    def perpendicular(self) -> vec2: ...
    def project(self, other: Vec2Like) -> vec2: ...
    def rotated(self, angle: Number) -> vec2: ...
    def safe_normalized(self) -> vec2: ...
    def safe_scaled_to(self, length: Number) -> vec2: ...
    def scaled_to(self, length: Number) -> vec2: ...
    def signed_angle_to(self, other) -> float: ...
    def to_polar(self) -> tuple[float, float]: ...
    def __abs__(self) -> Any: ...
    def __add__(self, other: Vec2Like) -> vec2: ...
    def __eq__(self, other) -> bool: ...
    def __floordiv__(self, other) -> Any: ...
    def __ge__(self, other) -> bool: ...
    def __getitem__(self, index) -> float: ...
    def __gt__(self, other) -> bool: ...
    def __hash__(self) -> Any: ...
    def __le__(self, other) -> bool: ...
    def __len__(self) -> Literal[2]: ...
    def __lt__(self, other) -> bool: ...
    def __mul__(self, other) -> vec2: ...
    def __ne__(self, other) -> bool: ...
    def __neg__(self) -> vec2: ...
    def __radd__(self, other) -> vec2: ...
    def __reduce__(self) -> Any: ...
    def __rfloordiv__(self, other) -> vec2: ...
    def __rmul__(self, other: Number) -> vec2: ...
    def __rsub__(self, other: Vec2Like) -> vec2: ...
    def __rtruediv__(self, other) -> vec2: ...
    def __setstate__(self, state) -> Any: ...
    def __sub__(self, other) -> vec2: ...
    def __truediv__(self, other: Number) -> vec2: ...


def bresenham(int64_tx0, int64_ty0, int64_tx1, int64_ty1) -> Any: ...
@overload
def v(*args) -> Any: ...
@overload
def v(x, y) -> Any: ...
