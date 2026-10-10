#!/usr/bin/env python3
"""Audit exported coupler CSV; no HFSS, network or third-party dependencies."""
import argparse
import csv
import json
import math
from pathlib import Path

HEADERS = ['Frequency_GHz', 'S3_TE01_dB', 'S4_TE01_dB',
           'Directivity_dB', 'S26_TE01_dB', 'S16_TE01_dB']


def analyze(path, target_ghz=24.0, minimum=None):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not set(HEADERS).issubset(reader.fieldnames):
            raise ValueError('Required CSV columns: ' + ', '.join(HEADERS))
        rows = []
        for line, raw in enumerate(reader, 2):
            row = {key: float(raw[key]) for key in HEADERS}
            if not all(math.isfinite(value) for value in row.values()):
                raise ValueError(f'Non-finite value at line {line}')
            if row['Frequency_GHz'] <= 0:
                raise ValueError(f'Non-positive frequency at line {line}')
            directivity = row['S3_TE01_dB'] - row['S4_TE01_dB']
            if abs(row['Directivity_dB'] - directivity) > 1e-6:
                raise ValueError(f'Directivity disagrees with S3-S4 at line {line}')
            row['coupling_loss_dB'] = -row['S3_TE01_dB']
            row['isolation_dB'] = -row['S4_TE01_dB']
            row['through_power_fraction'] = 10 ** (row['S26_TE01_dB'] / 10)
            rows.append(row)
    if not rows:
        raise ValueError('No data rows')
    frequencies = [row['Frequency_GHz'] for row in rows]
    if frequencies != sorted(set(frequencies)):
        raise ValueError('Frequencies must be unique and increasing')
    target = [row for row in rows if abs(row['Frequency_GHz'] - target_ghz) < 1e-8]
    if len(target) != 1:
        raise ValueError(f'Missing exact solved frequency {target_ghz} GHz; no interpolation performed')
    result = {'sample_count': len(rows), 'frequency_GHz': frequencies,
              'target': target[0], 'minimum_sampled_directivity_dB':
              min(row['Directivity_dB'] for row in rows)}
    if minimum is not None:
        result['target_meets_requested_directivity'] = target[0]['Directivity_dB'] >= minimum
        if not result['target_meets_requested_directivity']:
            raise ValueError(f'Target directivity {target[0]["Directivity_dB"]:.4f} dB is below {minimum} dB')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True, type=Path)
    parser.add_argument('--target-ghz', type=float, default=24.0)
    parser.add_argument('--min-directivity', type=float)
    args = parser.parse_args()
    try:
        result = analyze(args.csv, args.target_ghz, args.min_directivity)
    except (ValueError, KeyError, OSError, OverflowError) as error:
        parser.exit(2, f'Invalid coupler data: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
