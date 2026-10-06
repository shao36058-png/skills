"""Read saved modal data from one explicit HFSS session. Never submit a solve.

Requires PyAEDT/psutil and confirmed air/PEC ports. Mode identity, completeness,
and normalization remain pending until the engineer verifies the exported data.
"""
import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('version', 'project', 'design', 'solution', 'input-mode', 'target-mode'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--pec-ports', action='store_true', help='Confirm lossless air-filled PEC ports')
    parser.add_argument('--out', type=Path, required=True, help='New or empty directory')
    args = parser.parse_args()
    if not args.pec_ports:
        parser.error('Gamma classification requires confirmed air-filled PEC ports')
    if any(not re.fullmatch(r'[1-9]\d*:[1-9]\d*', mode) for mode in (args.input_mode, args.target_mode)):
        parser.error('Use explicit port:mode identifiers')
    if args.input_mode.split(':')[0] == args.target_mode.split(':')[0]:
        parser.error('Input and target must be on different physical ports')
    if ' : ' not in args.solution or ' - ' in args.solution:
        parser.error('Choose a normal setup : sweep; historical Table solutions need a separate audit')
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Output directory must be empty to preserve previous evidence')
    import psutil
    process = psutil.Process(args.pid)
    if process.name().lower() != 'ansysedt.exe':
        parser.error('PID is not a running AEDT desktop')
    if not any(c.status == psutil.CONN_LISTEN and c.laddr.port == args.port for c in process.net_connections(kind='tcp')):
        parser.error('Selected PID does not own the specified listener port')
    from ansys.aedt.core import Desktop, Hfss
    desktop = Desktop(version=args.version, port=args.port, aedt_process_id=args.pid,
                      new_desktop=False, close_on_exit=False)
    try:
        project = desktop.odesktop.GetActiveProject()
        if not project or project.GetName() != args.project:
            raise RuntimeError('Active project differs; no new project will be opened')
        design = project.GetActiveDesign()
        if not design or design.GetName().split(';')[-1] != args.design:
            raise RuntimeError('Active design differs; refusing to switch designs')
        h = Hfss(project=args.project, design=args.design, version=args.version,
                 port=args.port, aedt_process_id=args.pid, new_desktop=False, close_on_exit=False)
        if h.are_there_simulations_running:
            raise RuntimeError('A simulation is running; wait before auditing final data')
        if h.solution_type != 'Modal' or args.solution not in h.existing_analysis_sweeps:
            raise RuntimeError('Requested saved modal solution is unavailable')
        modes = sorted(h.excitation_names)
        if args.input_mode not in modes or args.target_mode not in modes:
            raise RuntimeError('Input or target is not represented')
        if {m.split(':')[0] for m in modes} != {args.input_mode.split(':')[0], args.target_mode.split(':')[0]}:
            raise RuntimeError('Only two physical waveguide ports are supported')
        expressions = [f'S({m},{args.input_mode})' for m in modes] + [f'Gamma({m})' for m in modes]
        variations = dict(h.available_variations.nominal_values)
        variations['Freq'] = ['All']
        data = h.post.get_solution_data(expressions=expressions, setup_sweep_name=args.solution,
                                       variations=variations, primary_sweep_variable='Freq',
                                       report_category='Modal Solution Data')
        if not data or len(data.variations) != 1:
            raise RuntimeError('No unique saved variation; choose one solved variation')
        factors = {'Hz': 1e-9, 'kHz': 1e-6, 'MHz': 1e-3, 'GHz': 1.0, 'THz': 1e3}
        unit = data.units_sweeps.get('Freq')
        if unit not in factors:
            raise RuntimeError(f'Unknown frequency unit: {unit}')
        payload = dict(frequencies_GHz=[float(f)*factors[unit] for f in data.primary_sweep_values],
                       input_mode=args.input_mode, target_mode=args.target_mode,
                       output_port=args.target_mode.split(':')[0], s_parameters={},
                       propagation_constants={}, propagating={},
                       evidence=dict(converged=False, mode_identity_verified=False,
                                     ports_complete=False, power_normalization_verified=False),
                       metadata=dict(project=args.project, design=args.design, solution=args.solution,
                                     variables={n:v.expression for n,v in h.variable_manager.variables.items()},
                                     active_solution_variation=data.active_variation,
                                     port_definitions={b.name:dict(b.props) for b in h.boundaries if b.type == 'Wave Port'},
                                     classification='Air/PEC: beta nonzero and alpha approximately zero',
                                     sweep_kind='adaptive' if args.solution.endswith('LastAdaptive') else 'unknown'))
        for mode in modes:
            s, gamma = f'S({mode},{args.input_mode})', f'Gamma({mode})'
            payload['s_parameters'][mode] = dict(real=list(map(float,data.get_expression_data(s,'real')[1])),
                                                imag=list(map(float,data.get_expression_data(s,'imag')[1])))
            alpha = list(map(float,data.get_expression_data(gamma,'real')[1]))
            beta = list(map(float,data.get_expression_data(gamma,'imag')[1]))
            payload['propagation_constants'][mode] = dict(alpha_per_m=alpha, beta_per_m=beta)
            payload['propagating'][mode] = [abs(b)>1e-6 and abs(a)<=max(1e-6,abs(b)*1e-4) for a,b in zip(alpha,beta)]
        setup_name, sweep_name = args.solution.split(' : ',1)
        setup = h.get_setup(setup_name)
        payload['metadata']['adaptive_setup'] = dict(setup.props)
        for sweep in setup.sweeps:
            if sweep.name == sweep_name:
                payload['metadata']['sweep_kind'] = str(sweep.props['Type'])
                payload['metadata']['sweep_definition'] = dict(sweep.props)
        out.mkdir(parents=True, exist_ok=True)
        convergence_path = out/'convergence.txt'
        h.export_convergence(setup_name, output_file=str(convergence_path))
        if convergence_path.exists():
            convergence_text = convergence_path.read_text(encoding='utf-8', errors='replace')
            payload['evidence']['converged'] = re.search(r'Converged\s*:\s*Yes\b', convergence_text, re.I) is not None
        (out/'modal_data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8')
        print(json.dumps(dict(exported=str(out/'modal_data.json'), samples=len(payload['frequencies_GHz']), evidence=payload['evidence']),ensure_ascii=False))
        return 0
    finally:
        desktop.release_desktop(close_projects=False,close_on_exit=False)


if __name__ == '__main__':
    raise SystemExit(main())
