"""Independent point-sampling audit. Does not import the region solver."""
import math
import time


def accepts(scene, point, observation_ids=None):
    x, y = point
    xmin, ymin, xmax, ymax = scene['bounds']
    if not (xmin <= x <= xmax and ymin <= y <= ymax):
        return False
    landmarks = {p['id']: (p['x'], p['y']) for p in scene['landmarks']}
    selected = set(scene.get('default_observations', [o['id'] for o in scene['observations']]) if observation_ids is None else observation_ids)
    for obs in scene['observations']:
        if obs['id'] not in selected:
            continue
        rays = [(landmarks[k][0] - x, landmarks[k][1] - y) for k in obs['landmarks']]
        if any(a == 0 and b == 0 for a, b in rays):
            return False
        if obs['kind'] == 'bearing':
            direction = (math.cos(math.radians(obs['value_deg'])), math.sin(math.radians(obs['value_deg'])))
            ray = rays[0]
            error = math.degrees(math.atan2(abs(ray[0]*direction[1]-ray[1]*direction[0]),
                                            ray[0]*direction[0]+ray[1]*direction[1]))
        elif obs['kind'] == 'angle':
            a, b = rays
            measured = math.degrees(math.atan2(abs(a[0]*b[1]-a[1]*b[0]), a[0]*b[0]+a[1]*b[1]))
            error = abs(measured - obs['value_deg'])
        else:
            raise ValueError('Unknown observation kind')
        if error > obs['tolerance_deg'] + 1e-10:
            return False
    return True


def dense_grid(scene, n, observation_ids=None):
    if not isinstance(n, int) or n <= 0:
        raise ValueError('n must be a positive integer')
    start = time.perf_counter()
    xmin, ymin, xmax, ymax = scene['bounds']
    dx, dy = (xmax-xmin)/n, (ymax-ymin)/n
    points = [[xmin+(i+.5)*dx, ymin+(j+.5)*dy] for j in range(n) for i in range(n)
              if accepts(scene, (xmin+(i+.5)*dx, ymin+(j+.5)*dy), observation_ids)]
    return {'points': points, 'area': len(points)*dx*dy, 'runtime_ms': (time.perf_counter()-start)*1000,
            'resolution': n, 'sample_count': n*n, 'accepted_count': len(points), 'cell_area': dx*dy,
            'method': 'independent cell-center point sampling; empty samples do not certify conflict'}
