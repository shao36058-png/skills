"""Lossless air/PEC circular and rectangular guide cutoff checks; standard library.

The circular counter resolves Bessel roots numerically for k0*radius <= 12.
It counts both polarizations of every m>0 mode. It does not assign HFSS indices.
"""
import argparse
import json
import math

C0 = 299792458.0


def bessel_j(order, x):
    term = (x / 2) ** order / math.factorial(order)
    terms = [term]
    for k in range(1, 160):
        term *= -(x * x / 4) / (k * (k + order))
        terms.append(term)
        if abs(term) < 1e-17 * max(1.0, abs(math.fsum(terms))):
            break
    return math.fsum(terms)


def derivative(order, x):
    return -bessel_j(1, x) if order == 0 else (bessel_j(order - 1, x) - bessel_j(order + 1, x)) / 2


def positive_roots(function, upper):
    roots = []
    left, f_left = 0.001, function(0.001)
    while left < upper:
        right = min(left + 0.025, upper)
        f_right = function(right)
        if f_left * f_right < 0:
            lo, hi, f_lo = left, right, f_left
            for _ in range(48):
                mid = (lo + hi) / 2
                f_mid = function(mid)
                if f_lo * f_mid <= 0:
                    hi = mid
                else:
                    lo, f_lo = mid, f_mid
            root = (lo + hi) / 2
            if not roots or abs(root - roots[-1]) > 1e-6:
                roots.append(root)
        left, f_left = right, f_right
    return roots


def circular_modes(radius_mm, upper_GHz):
    if not all(math.isfinite(v) and v > 0 for v in (radius_mm, upper_GHz)):
        raise ValueError('Radius and upper frequency must be finite and positive')
    size = 2 * math.pi * upper_GHz * 1e9 * radius_mm * 1e-3 / C0
    if size > 12:
        raise ValueError('k0*radius > 12: use a validated Bessel-root library or a port-only solution')
    modes = []
    for m in range(math.ceil(size) + 3):
        for family, function in [('TE', lambda x, m=m: derivative(m, x)), ('TM', lambda x, m=m: bessel_j(m, x))]:
            for n, root in enumerate(positive_roots(function, size + 1e-5), 1):
                cutoff = C0 * root / (2 * math.pi * radius_mm * 1e-3) / 1e9
                if cutoff <= upper_GHz + 1e-7:
                    modes.append(dict(family=family, m=m, n=n, root=root,
                                      cutoff_GHz=cutoff, degeneracy=1 if m == 0 else 2,
                                      near_cutoff=abs(cutoff - upper_GHz) < 0.001))
    return sorted(modes, key=lambda x: (x['cutoff_GHz'], x['family'], x['m']))


def rectangular_modes(a_mm, b_mm, upper_GHz):
    if not all(math.isfinite(v) and v > 0 for v in (a_mm, b_mm, upper_GHz)):
        raise ValueError('Dimensions and upper frequency must be finite and positive')
    m_max = math.floor(2 * a_mm * 1e-3 * upper_GHz * 1e9 / C0) + 1
    n_max = math.floor(2 * b_mm * 1e-3 * upper_GHz * 1e9 / C0) + 1
    if m_max * n_max > 100000:
        raise ValueError('Guide is too electrically large for this diagnostic helper')
    modes = []
    for m in range(m_max + 1):
        for n in range(n_max + 1):
            if m == n == 0:
                continue
            cutoff = C0 / 2 * math.hypot(m / (a_mm * 1e-3), n / (b_mm * 1e-3)) / 1e9
            if cutoff <= upper_GHz + 1e-7:
                for family in (['TE', 'TM'] if m and n else ['TE']):
                    modes.append(dict(family=family, m=m, n=n, cutoff_GHz=cutoff, degeneracy=1))
    return sorted(modes, key=lambda x: (x['cutoff_GHz'], x['family']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upper-GHz', type=float, required=True)
    shape = parser.add_mutually_exclusive_group(required=True)
    shape.add_argument('--radius-mm', type=float)
    shape.add_argument('--rectangle-mm', type=float, nargs=2, metavar=('A', 'B'))
    args = parser.parse_args()
    try:
        modes = circular_modes(args.radius_mm, args.upper_GHz) if args.radius_mm is not None else rectangular_modes(*args.rectangle_mm, args.upper_GHz)
        print(json.dumps(dict(assumptions='uniform air-filled PEC guide, no symmetry reduction',
                              upper_GHz=args.upper_GHz, propagating_channels=sum(m['degeneracy'] for m in modes),
                              modes=modes, note='Near-cutoff channels require margin. This does not identify HFSS mode numbers.'), indent=2))
        return 0
    except ValueError as exc:
        print(json.dumps(dict(error=str(exc))))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
