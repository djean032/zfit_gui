"""
Script to convert .pzy and .all files to CSV + TOML format for fitting.

.pzy format contains:
- Beam parameters (lambda_nm, tFWHM_s, pulseEnergy_J, w0_um, beamProfile, topHatFnumber, Msquared)
- Sample parameters (sampleThickness_cm, indexOfRefraction, Tsurf, activeMoleculeDensity, molarity)
- Material parameters (sigma_S0S1, molarAbsorptivity, sigma_S1S2, sigma_T3T4, sigma_S2, sigma_T4, twoPhotonSigma_cm4_W)
- Time constants (t10_s, t13_s, tripletYield, t21_s, t30_s, t43_s)
- Data table (z_mm, Tnorm)

.all format contains:
- Raw data (z(mm), ai0, ai1, ai2)

Output format:
- CSV: z(mm), ai0, ai1
- TOML: laser and sample parameters
"""

import re
from pathlib import Path

import numpy as np
import toml


def parse_pzy_file(filepath):
    """Parse a .pzy parameter file and extract configuration and data."""
    params = {}
    data_lines = []
    in_data_section = False

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("%"):
                continue

            # Check for data section marker
            if line == "$":
                in_data_section = True
                continue

            if in_data_section:
                # Data section: z_mm Tnorm
                data_lines.append(line)
            else:
                # Parameter section: key value
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    key, value = parts
                    # Try to convert to number
                    try:
                        if "E" in value or "e" in value:
                            params[key] = float(value)
                        else:
                            params[key] = float(value)
                    except ValueError:
                        params[key] = value

    # Parse data table
    z_values = []
    tnorm_values = []
    for line in data_lines:
        parts = line.split()
        if len(parts) >= 2:
            # Skip header line (contains 'z_mm' or non-numeric first column)
            try:
                z_val = float(parts[0])
                tnorm_val = float(parts[1])
                z_values.append(z_val)
                tnorm_values.append(tnorm_val)
            except ValueError:
                # Skip header lines
                continue

    return params, np.array(z_values), np.array(tnorm_values)


def parse_all_file(filepath):
    """Parse a .all file and extract raw data."""
    data_lines = []

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("%"):
                continue

            # Check if line looks like data (starts with number)
            parts = line.split()
            if len(parts) >= 3:
                try:
                    float(parts[0])  # First column should be z position
                    data_lines.append(line)
                except ValueError:
                    # Might be a parameter line
                    if len(parts) == 2:
                        pass  # Skip single key-value pairs

    # Parse data table
    z_values = []
    ai0_values = []
    ai1_values = []
    for line in data_lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                z_val = float(parts[0])
                ai0_val = float(parts[1])
                ai1_val = float(parts[2])
                z_values.append(z_val)
                ai0_values.append(ai0_val)
                ai1_values.append(ai1_val)
            except ValueError:
                # Skip header lines
                continue

    return np.array(z_values), np.array(ai0_values), np.array(ai1_values)


def create_config_from_pzy(pzy_params):
    """Convert .pzy parameters to the fitting program's config format."""
    config = {"experiment": {}, "laser": {}, "sample": {}}

    # Laser parameters (with unit conversions)
    # Convert nm to m
    if "lambda_nm" in pzy_params:
        config["laser"]["lambda_laser"] = pzy_params["lambda_nm"] * 1e-9

    # Pulse width (already in seconds)
    if "tFWHM_s" in pzy_params:
        config["laser"]["pulse_width"] = pzy_params["tFWHM_s"]

    # Pulse energy (in Joules)
    if "pulseEnergy_J" in pzy_params:
        config["laser"]["energy_pulse"] = pzy_params["pulseEnergy_J"]

    # Convert um to m for beam waist
    if "w0_um" in pzy_params:
        config["laser"]["w_0"] = pzy_params["w0_um"] * 1e-6

    # M-squared parameter
    if "Msquared" in pzy_params:
        config["laser"]["m_squared"] = pzy_params["Msquared"]

    # Sample parameters
    if "sampleThickness_cm" in pzy_params:
        config["sample"]["thickness"] = pzy_params["sampleThickness_cm"]

    if "Tsurf" in pzy_params:
        config["sample"]["T_surf"] = pzy_params["Tsurf"]

    # Concentration - use molarity if available, otherwise convert from activeMoleculeDensity
    if "molarity" in pzy_params:
        config["sample"]["concentration"] = pzy_params["molarity"]
    elif "activeMoleculeDensity" in pzy_params:
        # Convert molecules/cm^3 to molarity (mol/L)
        # 1 molarity = Avogadro's number per liter = 6.022e23 per 1000 cm^3
        config["sample"]["concentration"] = pzy_params["activeMoleculeDensity"] / 6.022e20

    # Cross-section parameters
    if "sigma_S0S1" in pzy_params:
        config["sample"]["sig_g"] = pzy_params["sigma_S0S1"]

    if "molarAbsorptivity" in pzy_params:
        config["sample"]["mol_abs"] = pzy_params["molarAbsorptivity"]

    # These need confirmation - mapping S1S2 and T3T4
    if "sigma_S1S2" in pzy_params:
        config["sample"]["sig_s"] = pzy_params["sigma_S1S2"]

    if "sigma_T3T4" in pzy_params:
        config["sample"]["sig_t"] = pzy_params["sigma_T3T4"]

    # sig_s2 and sig_t2 - need clarification on what these map to
    # For now, using sigma_S2 and sigma_T4 if available, or default values
    if "sigma_S2" in pzy_params:
        config["sample"]["sig_s2"] = pzy_params["sigma_S2"]
    else:
        config["sample"]["sig_s2"] = 1.0e-18

    if "sigma_T4" in pzy_params:
        config["sample"]["sig_t2"] = pzy_params["sigma_T4"]
    else:
        config["sample"]["sig_t2"] = 1.0e-18

    # Time constants
    if "t10_s" in pzy_params:
        config["sample"]["t_10"] = pzy_params["t10_s"]

    if "t13_s" in pzy_params:
        config["sample"]["t_13"] = pzy_params["t13_s"]

    if "t21_s" in pzy_params:
        config["sample"]["t_21"] = pzy_params["t21_s"]

    if "t30_s" in pzy_params:
        config["sample"]["t_30"] = pzy_params["t30_s"]

    if "t43_s" in pzy_params:
        config["sample"]["t_43"] = pzy_params["t43_s"]

    # Store original pulse energy in experiment section for reference
    if "pulseEnergy_J" in pzy_params:
        config["experiment"]["pulse_energy"] = pzy_params["pulseEnergy_J"]

    return config


def extract_energy_from_filename(filename):
    """Extract pulse energy from filename (e.g., '50 nJ' from '3-Br-pbt_532 nm_50 nJ.pzy')."""
    # Look for patterns like "50 nJ", "103.2 nJ", etc.
    match = re.search(r"(\d+\.?\d*)\s*(nJ|uJ|µJ|mJ|J)", filename, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).lower()

        # Convert to Joules
        if unit == "nj":
            return value * 1e-9
        elif unit in ["uj", "µj"]:
            return value * 1e-6
        elif unit == "mj":
            return value * 1e-3
        elif unit == "j":
            return value

    return None


def convert_files(data_dir, output_dir=None):
    """Convert .pzy and .all files to CSV + TOML format."""
    if output_dir is None:
        output_dir = data_dir

    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all .pzy files
    pzy_files = list(data_dir.glob("*.pzy"))

    print(f"Found {len(pzy_files)} .pzy files to convert")

    for pzy_file in pzy_files:
        # Look for corresponding .all file
        all_file = pzy_file.with_suffix(".all")
        if not all_file.exists():
            # Try variations in naming
            base_name = pzy_file.stem
            all_file = data_dir / f"{base_name}.all"

        if not all_file.exists():
            print(f"Warning: No .all file found for {pzy_file.name}, skipping...")
            continue

        print(f"\nProcessing: {pzy_file.name}")

        # Parse files
        pzy_params, z_pzy, tnorm = parse_pzy_file(pzy_file)
        z_all, ai0, ai1 = parse_all_file(all_file)

        # Create config from .pzy parameters
        config = create_config_from_pzy(pzy_params)

        # Override pulse energy from filename if there's a discrepancy
        filename_energy = extract_energy_from_filename(pzy_file.name)
        if filename_energy is not None:
            file_energy = config["laser"].get("energy_pulse", 0)
            if abs(filename_energy - file_energy) / max(filename_energy, file_energy) > 0.1:
                print(f"  Note: Pulse energy discrepancy - file: {file_energy:.2e} J, filename: {filename_energy:.2e} J")
                print(f"  Using filename value: {filename_energy:.2e} J")
                config["laser"]["energy_pulse"] = filename_energy
                config["experiment"]["pulse_energy"] = filename_energy

        # Create output filenames
        # Use molecule name and energy from filename
        base = pzy_file.stem.replace(" ", "_")
        csv_file = output_dir / f"{base}.csv"
        toml_file = output_dir / f"{base}.toml"

        # Create CSV with raw data
        csv_data = np.column_stack([z_all, ai0, ai1])
        np.savetxt(csv_file, csv_data, delimiter=",", header="z(mm),ai0,ai1", comments="")

        # Create TOML sidecar
        with open(toml_file, "w") as f:
            toml.dump(config, f)

        print(f"  Created: {csv_file.name}")
        print(f"  Created: {toml_file.name}")
        print(f"  Pulse energy: {config['laser']['energy_pulse']:.2e} J")


if __name__ == "__main__":
    # Convert files in the 3-Br directory
    data_dir = Path(__file__).parent / "data" / "3-Br"
    convert_files(data_dir)
