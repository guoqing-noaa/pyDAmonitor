#!/usr/bin/env python
import netCDF4 as nc
import numpy as np
import argparse
import warnings
import shapely.geometry as sg
from collections import defaultdict

"""
This program outputs the computational domain edge in a YAML format expected by the UFO Polygon Filter.
It has been updated to accept low_tol and high_tol as parameters, with updated defaults for buffer and high_tol.
NOTE: this program was intially developed by Sam Trahan and then expaned by Sijie Pan by including the simplify capability
"""

# Disable warnings
warnings.filterwarnings('ignore')


def normalize_lon(lon):
    lon = np.asarray(lon)
    return np.where(lon < 0.0, lon + 360.0, lon)


def to_plain_array(a):
    # netCDF masked arrays to plain ndarray
    return np.array(a.filled(np.nan)) if np.ma.isMaskedArray(a) else np.array(a)


def polygon_from_structured_edges(grid_ds):
    """
    Build a domain boundary ring from a structured FV3-style grid using only
    the outer perimeter (no triangulation). Works for variables named either
    (grid_lat, grid_lon) or (grid_latt, grid_lont).
    """
    vars_ = grid_ds.variables
    # Accept common FV3 names
    if 'grid_lat' in vars_ and 'grid_lon' in vars_:
        glat = np.array(vars_['grid_lat'][:])
        glon = np.array(vars_['grid_lon'][:])
    elif 'grid_latt' in vars_ and 'grid_lont' in vars_:
        glat = np.array(vars_['grid_latt'][:])
        glon = np.array(vars_['grid_lont'][:])
    else:
        raise RuntimeError(
            "Structured grid expected but did not find grid_lat/grid_lon or grid_latt/grid_lont."
        )

    if glat.ndim != 2 or glon.ndim != 2 or glat.shape != glon.shape:
        raise RuntimeError("grid_lat/grid_lon must be 2-D arrays of the same shape.")

    # Normalize longitudes to [0,360)
    glon = normalize_lon(glon)

    # Extract perimeter in CCW order: top > right > bottom > left
    top = np.c_[glon[0, :], glat[0, :]]
    right = np.c_[glon[1:, -1], glat[1:, -1]]
    bottom = np.c_[glon[-1, -2::-1], glat[-1, -2::-1]]     # exclude last to avoid dup
    left = np.c_[glon[-2:0:-1, 0], glat[-2:0:-1, 0]]     # exclude corners already used

    ring = np.vstack([top, right, bottom, left])
    return ring


def polygon_from_mpas_boundary(grid_ds):
    """
    Build the exact MPAS outer boundary by walking boundary edges.
    Returns ring as (N,2) [lon_deg, lat_deg] in [0,360) lon.
    """
    cellsOnEdge = to_plain_array(grid_ds.variables["cellsOnEdge"][:])   # (nEdges, 2), int
    verticesOnEdge = to_plain_array(grid_ds.variables["verticesOnEdge"][:])  # (nEdges, 2), int
    lonVertex = to_plain_array(grid_ds.variables["lonVertex"][:])     # (nVertices,)
    latVertex = to_plain_array(grid_ds.variables["latVertex"][:])

    # Convert to degrees; clean invalids
    lonv = np.degrees(lonVertex)
    latv = np.degrees(latVertex)
    goodv = np.isfinite(lonv) & np.isfinite(latv)
    if not goodv.all():
        pass

    # Boundary edges have a missing neighbor (cell id == 0)
    ce = cellsOnEdge.astype(np.int64)
    boundary_mask = (ce[:, 0] == 0) | (ce[:, 1] == 0)
    if not np.any(boundary_mask):
        raise RuntimeError("No boundary edges found (is this a global mesh?).")

    # Convert to 0-based; drop invalids (<=0) and edges that touch bad vertices
    bedges = verticesOnEdge[boundary_mask].astype(np.int64)  # 1-based indices
    v1 = bedges[:, 0] - 1
    v2 = bedges[:, 1] - 1
    ok = (v1 >= 0) & (v2 >= 0)
    if not goodv.all():
        ok &= goodv[v1] & goodv[v2]
    v1, v2 = v1[ok], v2[ok]

    # Build adjacency along boundary
    adj = defaultdict(list)
    for a, b in zip(v1, v2):
        adj[a].append(b)
        adj[b].append(a)

    # Walk loops to construct boundary
    visited_e = set()
    loops = []
    for s in list(adj.keys()):
        for nb in adj[s]:
            e = (min(s, nb), max(s, nb))
            if e in visited_e:
                continue
            ring_idx = [s, nb]
            visited_e.add(e)
            prev, cur = s, nb
            while True:
                nbs = adj[cur]
                nxt = nbs[0] if nbs[0] != prev else (nbs[1] if len(nbs) > 1 else None)
                if nxt is None:
                    break
                e2 = (min(cur, nxt), max(cur, nxt))
                if e2 in visited_e:
                    if nxt == ring_idx[0]:
                        loops.append(ring_idx)
                    break
                visited_e.add(e2)
                ring_idx.append(nxt)
                prev, cur = cur, nxt
                if cur == ring_idx[0]:
                    loops.append(ring_idx)
                    break

    if not loops:
        raise RuntimeError("Could not assemble a boundary loop from MPAS edges.")

    # Choose the largest loop (by vertex count)
    ring_ids = max(loops, key=len)

    # Compose lon/lat; normalize lon to [0,360)
    lon = lonv[ring_ids]
    lat = latv[ring_ids]
    lon = np.where(lon < 0.0, lon + 360.0, lon)
    ring = np.c_[lon, lat]

    return ring


def build_domain_ring(grid_ds):
    """
    Identifies the grid type and extracts the exact initial boundary ring.
    """
    varsin = grid_ds.variables.keys()
    if (('grid_lat' in varsin and 'grid_lon' in varsin) or ('grid_latt' in varsin and 'grid_lont' in varsin)):
        ring = polygon_from_structured_edges(grid_ds)
    elif {'cellsOnEdge', 'verticesOnEdge', 'lonVertex', 'latVertex'}.issubset(varsin):
        ring = polygon_from_mpas_boundary(grid_ds)
    else:
        raise RuntimeError("Unsupported grid file: need grid_lat/grid_lon (or grid_latt/grid_lont) or cells/verticesOnEdge")

    # Normalize and optionally fix the dateline seam
    ring[:, 0] = normalize_lon(ring[:, 0])
    L = ring[:, 0]
    span_direct = L.max() - L.min()
    L_shift = np.where(L > 180.0, L - 360.0, L)
    span_shift = L_shift.max() - L_shift.min()
    lon_offset = -360 if span_shift < span_direct else 0
    if lon_offset == -360:
        ring[:, 0] = L_shift
    return ring


def expand_and_simplify_ring(ring, buffer_deg=0.04, min_pts=40, max_pts=80, low_tol=0.001, high_tol=0.16):
    """
    Expands the domain ring outward and dynamically simplifies it.
    Uses 'buffer_deg + tol' to guarantee that the final simplified polygon
    never shrinks inside the guaranteed safety margin of buffer_deg.
    """
    poly = sg.Polygon(ring)
    best_poly = None

    # Run binary search within the specified low_tol and high_tol bounds
    for _ in range(20):
        tol = (low_tol + high_tol) / 2.0

        # PADDING TRICK: Expand by (buffer + tol). Even if simplify shaves off 'tol'
        # distance at the corners, the final boundary remains >= buffer_deg away.
        current_buffer = buffer_deg + tol

        buffered_poly = poly.buffer(current_buffer, join_style=2)
        simplified = buffered_poly.simplify(tol, preserve_topology=True)

        num_pts = len(simplified.exterior.coords) - 1

        # Keep track of the current result
        best_poly = simplified

        if min_pts <= num_pts <= max_pts:
            break
        elif num_pts > max_pts:
            low_tol = tol
        else:
            high_tol = tol

    # Fallback safety check: ensure the final used geometry incorporates the padding
    if best_poly is None:
        best_poly = poly.buffer(buffer_deg + low_tol, join_style=2).simplify(low_tol, preserve_topology=True)

    new_ring = np.array(best_poly.exterior.coords)[:-1]
    return new_ring


def print_ring(ring, lonlat, indent, columns=8):
    nring = len(ring)
    for i in range(nring):
        if i % columns == 0 and i < nring - 1:
            if i:
                print(',')
            print(indent, end='')
        elif i:
            print(', ', end='')
        print('%8.4f' % ring[i][lonlat], end='')


# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-g', '--grid', type=str, help='grid file', required=True)
parser.add_argument('-i', '--indent', type=str, help='indent', required=False, default='')
parser.add_argument('-b', '--buffer', type=float, help='buffer distance in degrees', required=False, default=0.04)
parser.add_argument('--min_pts', type=int, help='minimum allowed polygon vertices', required=False, default=40)
parser.add_argument('--max_pts', type=int, help='maximum allowed polygon vertices', required=False, default=80)
parser.add_argument('--low_tol', type=float, help='minimum simplification tolerance bound', required=False, default=0.001)
parser.add_argument('--high_tol', type=float, help='maximum simplification tolerance bound', required=False, default=0.16)
args = parser.parse_args()

# Assign filenames and arguments
grid_filename = args.grid
indent = args.indent
buffer_degree = args.buffer
min_pts = args.min_pts
max_pts = args.max_pts
low_tol = args.low_tol
high_tol = args.high_tol

grid_ds = nc.Dataset(grid_filename, 'r')

# Build the exact ring
ring = build_domain_ring(grid_ds)

# Apply precision expansion and geometric simplification using user arguments
ring = expand_and_simplify_ring(
    ring,
    buffer_deg=buffer_degree,
    min_pts=min_pts,
    max_pts=max_pts,
    low_tol=low_tol,
    high_tol=high_tol
)

# Calculate centroid based on the updated ring vertices
centroid = np.nanmean(ring, axis=0)

print(f'''{indent}polygon: &POLY
{indent}  filter: Polygon Check
{indent}  action:
{indent}    name: reduce obs space
{indent}  inside point longitude: {centroid[0]:.4f}
{indent}  inside point latitude: {centroid[1]:.4f}''')

print(f'{indent}  vertex longitudes: [')
print_ring(ring, 0, f'{indent}    ')
print(f'\n{indent}  ]')

print(f'{indent}  vertex latitudes: [')
print_ring(ring, 1, f'{indent}    ')
print(f'\n{indent}  ]')
