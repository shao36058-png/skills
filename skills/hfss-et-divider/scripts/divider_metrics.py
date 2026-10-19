#!/usr/bin/env python3
"""Audit exported complex divider S parameters offline; Python standard library only.

The input schema uses frequencies_GHz and data[expression][real|imag] arrays.
Existing summary metrics are ignored. Exit: 0 pass, 1 failed requested checks,
2 invalid input/arguments or an I/O error. No AEDT connection is made.
"""

import argparse
import cmath
import json
import math
from pathlib import Path
import re
import sys


class InputError(ValueError):
    """The input cannot be audited reliably."""


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{label} must be a number, not a boolean or string")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise InputError(f"{label} is outside the finite numeric range") from exc
    if not math.isfinite(value):
        raise InputError(f"{label} must be finite")
    return value


def finite_result(value, label):
    if not math.isfinite(value):
        raise InputError(f"{label} overflowed; check S-parameter scaling or parameters")
    return value


def numeric_array(value, label, expected_length=None):
    if not isinstance(value, list) or not value:
        raise InputError(f"{label} must be a nonempty array")
    if expected_length is not None and len(value) != expected_length:
        raise InputError(
            f"{label} has {len(value)} values; expected {expected_length}"
        )
    return [number(item, f"{label}[{i}]") for i, item in enumerate(value)]


def reject_constant(value):
    raise InputError(f"Nonstandard JSON numeric constant {value!r} is not allowed")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def read_input(path):
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8-sig"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON: {exc}") from exc


def wrapped_degrees(value):
    """Return an angle in [-180, 180); +180 and -180 are equivalent."""
    return (value + 180.0) % 360.0 - 180.0


def db(magnitude):
    return 20.0 * math.log10(magnitude) if magnitude else None


def value_range(values):
    defined = [value for value in values if value is not None]
    return {
        "min": min(defined) if defined else None,
        "max": max(defined) if defined else None,
        "defined_sample_count": len(defined),
        "undefined_sample_count": len(values) - len(defined),
    }


def maximum_absolute(values):
    # A finite subset must not hide a zero-amplitude undefined sample.
    if any(value is None for value in values):
        return None
    return max(abs(value) for value in values)


MM_LITERAL = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*mm\s*$",
    re.IGNORECASE,
)


def geometry_from_parameters(parameters):
    required = ("a", "b", "c", "d", "iris_w", "iris_d", "iris_t",
                "iris2_w", "iris2_d")
    if not isinstance(parameters, dict):
        return {"available": False, "reason": "No parameter object was provided."}
    keys = required + (("iris2_t",) if "iris2_t" in parameters else ())
    parsed, unavailable = {}, []
    for key in keys:
        value = parameters.get(key)
        match = MM_LITERAL.fullmatch(value) if isinstance(value, str) else None
        if match is None:
            unavailable.append(key)
        else:
            parsed[key] = number(float(match.group(1)), f"parameters.{key}")
    if unavailable:
        return {
            "available": False,
            "reason": "Geometry requires all listed parameters as literal mm values; expressions and unitless values are not evaluated.",
            "missing_or_nonliteral_parameters": unavailable,
        }
    a, b, c, d = (parsed[key] for key in ("a", "b", "c", "d"))
    widths = [parsed["iris_w"], parsed["iris2_w"]]
    centers = [parsed["iris_d"], parsed["iris2_d"]]
    thicknesses = [parsed["iris_t"], parsed.get("iris2_t", parsed["iris_t"])]
    irises = []
    for width, center, thickness in zip(widths, centers, thicknesses):
        near, far = center - thickness / 2.0, center + thickness / 2.0
        irises.append({
            "opening_width_mm": width,
            "opening_half_width_mm": width / 2.0,
            "thickness_mm": thickness,
            "penetration_each_side_mm": (a - width) / 2.0,
            "center_from_junction_wall_mm": center,
            "near_face_from_junction_wall_mm": near,
            "far_face_from_junction_wall_mm": far,
            "center_global_y_mm": b / 2.0 + center,
            "near_face_global_y_mm": b / 2.0 + near,
            "far_face_global_y_mm": b / 2.0 + far,
        })
    separation = centers[1] - centers[0]
    gap = irises[1]["near_face_from_junction_wall_mm"] - irises[0]["far_face_from_junction_wall_mm"]
    port_gap = d - irises[1]["far_face_from_junction_wall_mm"]
    derived = {
        "available": True,
        "unit": "mm",
        "convention": "Symmetric x-directed irises; d_i measured from the T outer wall y=b/2; c is total collinear-arm length; d is branch length from that wall.",
        "parameters_mm": parsed,
        "irises": irises,
        "center_separation_mm": separation,
        "inter_iris_clear_gap_mm": gap,
        "second_far_face_to_input_port_mm": port_gap,
        "input_port_global_y_mm": b / 2.0 + d,
        "collinear_port_global_z_mm": [-c / 2.0, c / 2.0],
        "total_cavity_y_span_mm": b + d,
        "checks": {
            "positive_dimensions": all(value > 0 for value in [a, b, c, d] + widths + thicknesses),
            "openings_within_waveguide_width": all(0 < width <= a for width in widths),
            "first_near_face_after_junction_wall": irises[0]["near_face_from_junction_wall_mm"] > 0,
            "ordered_nonoverlapping_irises": gap > 0,
            "second_far_face_before_input_port": port_gap > 0,
        },
    }

    def check_derived(value):
        if isinstance(value, dict):
            for item in value.values():
                check_derived(item)
        elif isinstance(value, list):
            for item in value:
                check_derived(item)
        elif isinstance(value, float):
            finite_result(value, "Derived geometry")

    check_derived(derived)
    return derived


def audit(payload, reflection_expression="S(2:1,2:1)",
          output_expressions=("S(1:1,2:1)", "S(3:1,2:1)"),
          expected_phase_deg=180.0, max_reflection_db=None,
          min_frequency_ghz=None, max_frequency_ghz=None):
    if not isinstance(payload, dict):
        raise InputError("The JSON root must be an object")
    expressions = [reflection_expression] + list(output_expressions)
    if len(expressions) != 3 or len(set(expressions)) != 3:
        raise InputError("Select one reflection and two distinct output expressions")
    expected_phase_deg = number(expected_phase_deg, "expected_phase_deg")
    for label, value in (("max_reflection_db", max_reflection_db),
                         ("min_frequency_ghz", min_frequency_ghz),
                         ("max_frequency_ghz", max_frequency_ghz)):
        if value is not None:
            number(value, label)
    if (min_frequency_ghz is not None and max_frequency_ghz is not None
            and min_frequency_ghz > max_frequency_ghz):
        raise InputError("min_frequency_ghz must not exceed max_frequency_ghz")
    frequencies = numeric_array(payload.get("frequencies_GHz"), "frequencies_GHz")
    if any(right <= left for left, right in zip(frequencies, frequencies[1:])):
        raise InputError("frequencies_GHz must be strictly increasing")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise InputError("data must be an object indexed by S-parameter expression")
    magnitudes, phases, powers, decibels = [], [], [], []
    for expression in expressions:
        item = data.get(expression)
        if not isinstance(item, dict):
            raise InputError(f"Missing complex-array object data[{expression!r}]")
        real = numeric_array(item.get("real"), f"data[{expression!r}].real", len(frequencies))
        imag = numeric_array(item.get("imag"), f"data[{expression!r}].imag", len(frequencies))
        values = [complex(r, i) for r, i in zip(real, imag)]
        mag = [finite_result(abs(value), f"Magnitude of {expression}") for value in values]
        power = [finite_result(value * value, f"Power of {expression}") for value in mag]
        magnitudes.append(mag)
        powers.append(power)
        phases.append([math.degrees(cmath.phase(value)) if abs(value) else None for value in values])
        decibels.append([db(value) for value in mag])
    worst_index = max(range(len(frequencies)), key=magnitudes[0].__getitem__)
    worst_db = decibels[0][worst_index]
    reflection_percent = [finite_result(100.0 * value, "Reflection percent") for value in powers[0]]
    imbalance, relative_phase = [], []
    expected_normalized = wrapped_degrees(expected_phase_deg)
    for i in range(len(frequencies)):
        if not magnitudes[1][i] or not magnitudes[2][i]:
            imbalance.append(None)
            relative_phase.append(None)
        else:
            imbalance.append(decibels[1][i] - decibels[2][i])
            relative_phase.append(wrapped_degrees(phases[1][i] - phases[2][i]))
    expected_error = [wrapped_degrees(value - expected_normalized) if value is not None else None for value in relative_phase]
    error_180 = [wrapped_degrees(value - 180.0) if value is not None else None for value in relative_phase]
    try:
        power_sum = [finite_result(math.fsum(values), "Three-term power sum") for values in zip(*powers)]
    except OverflowError as exc:
        raise InputError("Three-term power sum overflowed") from exc
    residual = [1.0 - value for value in power_sum]
    checks = {}
    if max_reflection_db is not None:
        checks["maximum_reflection_db"] = {
            "limit_db": max_reflection_db,
            "observed_worst_db": worst_db,
            "passed": worst_db is None or worst_db <= max_reflection_db,
        }
    for label, target in (("minimum_frequency_coverage", min_frequency_ghz),
                          ("maximum_frequency_coverage", max_frequency_ghz)):
        if target is not None:
            checks[label] = {
                "requested_ghz": target,
                "passed": frequencies[0] - 1e-9 <= target <= frequencies[-1] + 1e-9,
                "absolute_tolerance_ghz": 1e-9,
            }
    geometry = geometry_from_parameters(payload.get("parameters"))
    notes = [
        "All metrics were recomputed from the selected complex arrays; input summary metrics were ignored.",
        "Power fractions assume power-normalized selected S parameters. The three-term residual is 1 minus the selected reflection and two transmissions; it is not an identified loss. Unselected modes, other channels, material losses, interpolation, and numerical error require separate interpretation.",
        "Frequency coverage checks apply to the available sample interval and do not prove a continuous-band bound or independent discrete solves.",
        "Relative phase is output_expressions[0] minus output_expressions[1], wrapped into [-180,180). Phase errors use the shortest wrapped angular difference.",
        "A null magnitude_dB denotes exact zero amplitude (mathematically minus infinity dB). A null phase or imbalance denotes a zero output amplitude. Maxima of phase/imbalance errors are null if any sample is undefined; null must not be interpreted as zero error.",
    ]
    if geometry.get("available") and not all(geometry["checks"].values()):
        notes.append("One or more derived-geometry checks failed under the stated convention; inspect the geometry before using these dimensions. Geometry checks do not change the requested RF threshold exit status.")
    report = {
        "schema_version": 1,
        "checks_passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
        "source_metadata": {key: payload[key] for key in ("setup_sweep", "sweep_type", "interpolation_tolerance_percent") if key in payload},
        "frequency": {"unit": "GHz", "count": len(frequencies), "min": frequencies[0], "max": frequencies[-1], "values": frequencies},
        "reflection": {
            "expression": expressions[0], "magnitude_dB": decibels[0],
            "power_fraction": powers[0], "power_percent": reflection_percent,
            "worst": {"index": worst_index, "frequency_GHz": frequencies[worst_index],
                      "magnitude_dB": worst_db, "power_fraction": powers[0][worst_index],
                      "power_percent": reflection_percent[worst_index]},
        },
        "outputs": [{"expression": expressions[i], "magnitude_dB": decibels[i],
                     "magnitude_dB_range": value_range(decibels[i]),
                     "power_fraction": powers[i], "power_fraction_range": value_range(powers[i])}
                    for i in (1, 2)],
        "amplitude_imbalance": {"signed_dB": imbalance, "max_abs_dB": maximum_absolute(imbalance),
                                "undefined_indices": [i for i, value in enumerate(imbalance) if value is None]},
        "phase": {"unit": "degree", "relative_deg": relative_phase,
                  "expected_phase_deg": expected_phase_deg,
                  "error_from_expected_deg": expected_error,
                  "max_abs_error_from_expected_deg": maximum_absolute(expected_error),
                  "error_from_180_deg": error_180,
                  "max_abs_error_from_180_deg": maximum_absolute(error_180),
                  "undefined_indices": [i for i, value in enumerate(relative_phase) if value is None]},
        "power_balance": {"three_term_sum": power_sum, "three_term_sum_range": value_range(power_sum),
                          "residual": residual, "residual_range": value_range(residual),
                          "max_abs_residual": max(abs(value) for value in residual)},
        "geometry": geometry,
        "notes": notes,
    }
    return report


def finite_argument(text):
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a finite number") from exc
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError("must be finite")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Exported complex S-parameter JSON")
    parser.add_argument("--output", type=Path, help="Write JSON here instead of stdout; input is never overwritten")
    parser.add_argument("--reflection-expression", default="S(2:1,2:1)")
    parser.add_argument("--output-expressions", nargs=2, default=["S(1:1,2:1)", "S(3:1,2:1)"])
    parser.add_argument("--expected-phase-deg", type=finite_argument, default=180.0)
    parser.add_argument("--max-reflection-db", type=finite_argument, help="Fail if worst reflection dB is greater than this limit")
    parser.add_argument("--min-frequency-ghz", type=finite_argument, help="Require this lower frequency to lie within available coverage; no cropping")
    parser.add_argument("--max-frequency-ghz", type=finite_argument, help="Require this upper frequency to lie within available coverage; no cropping")
    args = parser.parse_args(argv)
    try:
        if args.output is not None:
            same_path = args.output.resolve() == args.input.resolve()
            same_file = (args.output.exists() and args.input.exists()
                         and args.output.samefile(args.input))
            if same_path or same_file:
                raise InputError("--output must not overwrite --input")
        payload = read_input(args.input)
        report = audit(
            payload, args.reflection_expression, args.output_expressions,
            args.expected_phase_deg, args.max_reflection_db,
            args.min_frequency_ghz, args.max_frequency_ghz,
        )
        text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output is None:
            sys.stdout.write(text)
        else:
            args.output.write_text(text, encoding="utf-8")
        return 0 if report["checks_passed"] else 1
    except (InputError, OSError, UnicodeError, ValueError, OverflowError) as exc:
        print(f"divider_metrics: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
