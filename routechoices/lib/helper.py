import base64
import random
import struct

import requests

from routechoices.lib.random_strings import generate_random_alphabet_digit


def random_key():
    rand_bytes = bytes(struct.pack('Q', random.getrandbits(64)))
    b64 = base64.b64encode(rand_bytes).decode('utf-8')
    b64 = b64[:11]
    b64 = b64.replace('+', '-')
    b64 = b64.replace('/', '_')
    return b64


def short_random_key():
    return generate_random_alphabet_digit(str_len=6)


def get_country_from_coords(lat,lon):
    api_url = "http://api.geonames.org/countryCode"
    values = {
        'type': 'json',
        'lat': lat,
        'lng': lon,
        'username': 'rphl',
        'radius': 1
    }
    try:
        response = requests.get(api_url, params=values)
        return response.json().get('countryCode')
    except Exception:
        pass
    return None


def solve_affine_matrix(r1, s1, t1, r2, s2, t2, r3, s3, t3):
    a = (((t2 - t3) * (s1 - s2)) - ((t1 - t2) * (s2 - s3))) \
        / (((r2 - r3) * (s1 - s2)) - ((r1 - r2) * (s2 - s3)))
    b = (((t2 - t3) * (r1 - r2)) - ((t1 - t2) * (r2 - r3))) \
        / (((s2 - s3) * (r1 - r2)) - ((s1 - s2) * (r2 - r3)))
    c = t1 - (r1 * a) - (s1 * b)
    return a, b, c


def derive_affine_transform(a0, a1, b0, b1, c0, c1):
    x = solve_affine_matrix(
        a0.x, a0.y, a1.x,
        b0.x, b0.y, b1.x,
        c0.x, c0.y, c1.x)
    y = solve_affine_matrix(
        a0.x, a0.y, a1.y,
        b0.x, b0.y, b1.y,
        c0.x, c0.y, c1.y)
    return tuple(x + y)


def adjugate_matrix(m):
    return [
        m[4] * m[8] - m[5] * m[7], m[2] * m[7] - m[1] * m[8],
        m[1] * m[5] - m[2] * m[4],
        m[5] * m[6] - m[3] * m[8], m[0] * m[8] - m[2] * m[6],
        m[2] * m[3] - m[0] * m[5],
        m[3] * m[7] - m[4] * m[6], m[1] * m[6] - m[0] * m[7],
        m[0] * m[4] - m[1] * m[3]
    ]


def multiply_matrices(a, b):
    c = [0]*9
    for i in range(3):
        for j in range(3):
            for k in range(3):
                c[3 * i + j] += a[3 * i + k] * b[3 * k + j]
    return c


def multiply_matrix_vector(m, v):
    return [
        m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
        m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
        m[6] * v[0] + m[7] * v[1] + m[8] * v[2]
    ]


def basis_to_points(x1, y1, x2, y2, x3, y3, x4, y4):
    m = [
        x1, x2, x3,
        y1, y2, y3,
        1, 1, 1
    ]
    v = multiply_matrix_vector(adjugate_matrix(m), [x4, y4, 1])
    return multiply_matrices(m, [
        v[0], 0, 0,
        0, v[1], 0,
        0, 0, v[2]
    ])


def general_2d_projection(x1s, y1s, x1d, y1d,
                        x2s, y2s, x2d, y2d,
                        x3s, y3s, x3d, y3d,
                        x4s, y4s, x4d, y4d):
    s = basis_to_points(x1s, y1s, x2s, y2s, x3s, y3s, x4s, y4s)
    d = basis_to_points(x1d, y1d, x2d, y2d, x3d, y3d, x4d, y4d)
    return multiply_matrices(d, adjugate_matrix(s))


def project(m, x, y):
    v = multiply_matrix_vector(m, [x, y, 1])
    return v[0] / v[2], v[1] / v[2]
