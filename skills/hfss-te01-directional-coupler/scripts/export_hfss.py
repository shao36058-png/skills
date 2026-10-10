#!/usr/bin/env python3
"""Read saved HFSS coupler data from one explicitly selected existing Desktop."""
import argparse
import csv
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', required=True, type=int)
    parser.add_argument('--project', required=True, help='Exact name of an already-open project')
    parser.add_argument('--design', required=True)
    parser.add_argument('--version', default='2025.2')
    parser.add_argument('--aedt-root', type=Path)
    parser.add_argument('--solution', default='PhaseCheck24 : BandCheck')
    parser.add_argument('--input-mode', default='1:6', help='Verify TE01 field identity before choosing')
    parser.add_argument('--through-mode', default='2:6')
    parser.add_argument('--coupled-port', default='3')
    parser.add_argument('--isolated-port', default='4')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.aedt_root:
        if not (args.aedt_root / 'ansysedt.exe').is_file():
            parser.error('--aedt-root must contain ansysedt.exe')
        year, release = args.version.split('.')
        os.environ['ANSYSEM_ROOT' + year[-2:] + release] = str(args.aedt_root)
    import psutil
    if psutil.Process(args.pid).name().lower() != 'ansysedt.exe':
        parser.error('--pid is not an existing ansysedt.exe process')
    from ansys.aedt.core import Desktop, Hfss
    desktop = Desktop(version=args.version, new_desktop=False,
                      close_on_exit=False, aedt_process_id=args.pid)
    try:
        if args.project not in desktop.project_list:
            raise ValueError('Requested project is not already open; exporter will not create it')
        if args.design not in desktop.design_list(args.project):
            raise ValueError('Requested design does not exist; exporter will not create it')
        hfss = Hfss(project=args.project, design=args.design, version=args.version,
                    new_desktop=False, close_on_exit=False, aedt_process_id=args.pid)
        if hfss.are_there_simulations_running:
            raise ValueError('Desktop is solving; wait for completed saved results')
        if hfss.solution_type != 'Modal':
            raise ValueError('Driven Modal is required for this modal exporter')
        if args.solution not in hfss.existing_analysis_sweeps:
            raise ValueError('Requested solution not found: ' + args.solution)
        available = set(hfss.excitation_names)
        channels = [args.input_mode, args.through_mode, args.coupled_port, args.isolated_port]
        if any(channel not in available and f'{channel}:1' not in available for channel in channels):
            raise ValueError('One or more requested source/channel identifiers do not exist')
        destinations = [args.coupled_port, args.isolated_port, args.through_mode, args.input_mode]
        expressions = [f'dB(S({destination},{args.input_mode}))' for destination in destinations]
        data = hfss.post.get_solution_data(expressions=expressions, setup_sweep_name=args.solution)
        if not data:
            raise ValueError('No saved result for current variation and requested solution')
        unit = data.units_sweeps.get('Freq', '')
        factors = {'Hz': 1e-9, 'kHz': 1e-6, 'MHz': 1e-3, 'GHz': 1.0, 'THz': 1e3}
        if data.primary_sweep != 'Freq' or unit not in factors:
            raise ValueError(f'Unexpected sweep axis/unit: {data.primary_sweep}/{unit}')
        frequency = [float(x) * factors[unit] for x in data.primary_sweep_values]
        series = {e: [float(x) for x in data.get_expression_data(e, formula='real', convert_to_SI=False)[1]] for e in expressions}
        if any(len(values) != len(frequency) for values in series.values()):
            raise ValueError('Sweep/value length mismatch')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['Frequency_GHz', 'S3_TE01_dB', 'S4_TE01_dB',
                             'Directivity_dB', 'S26_TE01_dB', 'S16_TE01_dB'])
            for i, freq in sorted(enumerate(frequency), key=lambda item: item[1]):
                values = [series[e][i] for e in expressions]
                writer.writerow([freq, values[0], values[1], values[0]-values[1], values[2], values[3]])
        args.output.with_suffix('.metadata.json').write_text(json.dumps({
            'design': args.design, 'solution': args.solution,
            'input_mode': args.input_mode, 'through_mode': args.through_mode,
            'coupled_port': args.coupled_port, 'isolated_port': args.isolated_port,
            'expressions': expressions, 'frequency_unit': 'GHz',
            'read_only': True, 'mode_identity': 'User must verify field distribution',
        }, indent=2), encoding='utf-8')
        print(json.dumps({'rows': len(frequency), 'csv': str(args.output), 'read_only': True}))
    finally:
        desktop.release_desktop(close_projects=False, close_on_exit=False)


if __name__ == '__main__':
    main()
