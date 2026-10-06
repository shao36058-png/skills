"""Verify saved TE01 power samples without connecting to HFSS."""
import argparse
import csv
import json
import math
from pathlib import Path


def verify_band(csv_path, center_ghz=28.0, band_start=27.5, band_end=28.5,
                expected_points=101, center_min=0.98, band_min=0.96):
    if expected_points < 2 or not band_start <= center_ghz <= band_end or band_start >= band_end:
        raise ValueError('Invalid frequency specification')
    samples=[]
    with Path(csv_path).open(encoding='utf-8-sig', newline='') as source:
        reader=csv.DictReader(source)
        required={'frequency_GHz','TE01_transmission_power'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Missing frequency_GHz or TE01_transmission_power column')
        for row in reader:
            frequency=float(row['frequency_GHz'])
            power=float(row['TE01_transmission_power'])
            if not math.isfinite(frequency) or not math.isfinite(power) or power < 0:
                raise ValueError('Nonfinite frequency/power or negative power')
            samples.append((frequency,power))
    samples.sort()
    if len(samples) != expected_points:
        raise ValueError(f'Expected {expected_points} points, found {len(samples)}')
    step=(band_end-band_start)/(expected_points-1)
    for index,(frequency,power) in enumerate(samples):
        if abs(frequency-(band_start+index*step)) > 1e-8:
            raise ValueError('Missing, duplicate, or off-grid frequency')
    center_samples=[power for frequency,power in samples if abs(frequency-center_ghz) < 1e-8]
    if len(center_samples) != 1:
        raise ValueError('Exactly one explicit center-frequency sample is required')
    lowest=min(samples,key=lambda sample:sample[1])
    center_power=center_samples[0]
    return {
        'scope':'Saved CSV sampled-frequency check; no new HFSS solution or continuous-band proof',
        'csv':str(Path(csv_path).resolve()),
        'sample_count':len(samples),
        'band_GHz':[band_start,band_end],
        'center_TE01_power':center_power,
        'band_min_sampled_TE01_power':lowest[1],
        'band_min_frequency_GHz':lowest[0],
        'center_requirement':center_min,
        'band_requirement':band_min,
        'center_passed':center_power > center_min,
        'band_passed':lowest[1] > band_min,
        'passed':center_power > center_min and lowest[1] > band_min,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path,required=True)
    parser.add_argument('--center-ghz',type=float,default=28.0)
    parser.add_argument('--band-start',type=float,default=27.5)
    parser.add_argument('--band-end',type=float,default=28.5)
    parser.add_argument('--points',type=int,default=101)
    parser.add_argument('--center-min',type=float,default=0.98)
    parser.add_argument('--band-min',type=float,default=0.96)
    parser.add_argument('--out',type=Path)
    options=parser.parse_args()
    try:
        result=verify_band(options.csv,options.center_ghz,options.band_start,options.band_end,
                           options.points,options.center_min,options.band_min)
    except (OSError,ValueError) as error:
        parser.exit(2,f'Invalid saved data: {error}\n')
    rendered=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)
    print(rendered)
    if options.out:
        options.out.write_text(rendered+'\n',encoding='utf-8')
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
