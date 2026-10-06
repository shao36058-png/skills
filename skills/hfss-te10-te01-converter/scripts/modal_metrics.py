"""Audit saved, power-normalized modal S data; never attach to or solve HFSS.

JSON schema: frequencies_GHz, input_mode, output_port, target_mode,
s_parameters[mode]={real:[],imag:[]}, propagating[mode]=[bool,...],
evidence={converged:bool,mode_identity_verified:bool,ports_complete:bool,
power_normalization_verified:bool}, metadata={sweep_kind:str,...}.
Only propagating channels count toward a real-power budget.
"""
import argparse
import json
import math
from pathlib import Path

EVIDENCE_KEYS = ('converged', 'mode_identity_verified', 'ports_complete', 'power_normalization_verified')


def audit(payload):
    frequencies = payload['frequencies_GHz']
    if not frequencies or any(type(f) not in (int, float) or not math.isfinite(f) or f <= 0 for f in frequencies):
        raise ValueError('Frequencies must be finite, positive numbers')
    if len(set(frequencies)) != len(frequencies):
        raise ValueError('Duplicate frequencies are not valid acceptance evidence')
    incident, output_port, target = payload['input_mode'], str(payload['output_port']), payload['target_mode']
    parameters, propagating = payload['s_parameters'], payload['propagating']
    if not all(isinstance(mode, str) and len(mode.split(':')) == 2 and all(part.isdigit() and int(part) > 0 for part in mode.split(':')) for mode in parameters):
        raise ValueError('Mode keys must be explicit port:mode identifiers')
    input_port = incident.split(':')[0]
    if target.split(':')[0] != output_port or input_port == output_port:
        raise ValueError('Input and output port identities are inconsistent')
    if incident not in parameters or target not in parameters or set(parameters) != set(propagating):
        raise ValueError('S data and propagation masks must cover the same represented modes')
    if any(mode.split(':')[0] not in (input_port, output_port) for mode in parameters):
        raise ValueError('This helper supports two physical waveguide ports only')
    count = len(frequencies)
    powers = {}
    for mode, values in parameters.items():
        reals, imags, mask = values['real'], values['imag'], propagating[mode]
        if len(reals) != count or len(imags) != count or len(mask) != count or any(type(v) is not bool for v in mask):
            raise ValueError(f'Incomplete arrays or invalid propagation mask for {mode}')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in reals + imags):
            raise ValueError(f'Nonfinite or invalid S data for {mode}')
        powers[mode] = [a*a + b*b for a, b in zip(reals, imags)]
        if any(not math.isfinite(v) for v in powers[mode]):
            raise ValueError(f'Overflow in S power for {mode}')
    rows = []
    for index in sorted(range(count), key=frequencies.__getitem__):
        if not propagating[incident][index] or not propagating[target][index]:
            raise ValueError('Incident and target channels must propagate at each evaluated frequency')
        reflection = math.fsum(v[index] for mode, v in powers.items() if mode.split(':')[0] == input_port and propagating[mode][index])
        transmission = math.fsum(v[index] for mode, v in powers.items() if mode.split(':')[0] == output_port and propagating[mode][index])
        target_power = powers[target][index]
        if transmission <= 0:
            raise ValueError('Mode purity is undefined with zero represented transmission')
        rows.append(dict(frequency_GHz=frequencies[index], target_efficiency=target_power,
                         insertion_loss_dB=-10*math.log10(target_power) if target_power else None,
                         represented_total_transmission=transmission,
                         represented_reflection=reflection,
                         represented_parasitic_transmission=transmission-target_power,
                         represented_mode_purity=target_power/transmission,
                         power_budget_residual=1-reflection-transmission))
    evidence = payload.get('evidence', {})
    pending = [key for key in EVIDENCE_KEYS if evidence.get(key) is not True]
    if any(row['power_budget_residual'] < -1e-4 for row in rows):
        pending.append('represented_power_exceeds_incident_power')
    return dict(input_mode=incident, target_mode=target, sample_count=count,
                scope='Saved samples only; represented channels only. This does not rerun or certify HFSS.',
                sweep_kind=payload.get('metadata', {}).get('sweep_kind', 'unknown'),
                pending_evidence=pending, engineering_verified=not pending,
                minimum_target_efficiency=min(rows, key=lambda x: x['target_efficiency']),
                maximum_abs_budget_residual=max(abs(row['power_budget_residual']) for row in rows), rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path, required=True)
    parser.add_argument('--min-efficiency', type=float)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.min_efficiency is not None and (not math.isfinite(args.min_efficiency) or not 0 <= args.min_efficiency <= 1):
            raise ValueError('Minimum efficiency must be between 0 and 1')
        payload = json.loads(args.json.read_text(encoding='utf-8'))
        result = audit(payload)
        result['threshold'] = args.min_efficiency
        result['sampled_threshold_met'] = None if args.min_efficiency is None else all(row['target_efficiency'] > args.min_efficiency for row in result['rows'])
        result['acceptance_passed'] = result['engineering_verified'] and result['sampled_threshold_met'] is True
        output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            if args.output.resolve() == args.json.resolve():
                raise ValueError('Output must not overwrite input evidence')
            args.output.write_text(output+'\n', encoding='utf-8')
        print(output)
        if args.min_efficiency is None:
            return 0
        return 2 if not result['engineering_verified'] else (0 if result['sampled_threshold_met'] else 1)
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps(dict(error=str(exc)), ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
