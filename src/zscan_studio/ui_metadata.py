LASER_LABELS: dict[str, str] = {
    "lambda_laser": "λ<sub>laser</sub> (wavelength, m):",
    "energy_pulse": "E<sub>pulse</sub> (pulse energy, J):",
    "pulse_width": "Pulse width (s):",
    "w_0": "w<sub>0</sub> (beam waist, m):",
    "m_squared": "M<sup>2</sup> (beam quality factor):",
}

SAMPLE_LABELS: dict[str, str] = {
    "thickness": "d (sample thickness, cm):",
    "T_surf": "T<sub>surf</sub> (surface transmission):",
    "concentration": "C (concentration, M):",
    "sig_g": "σ<sub>G</sub> (ground-state absorption cross-section):",
    "mol_abs": "ε (molar absorptivity):",
    "sig_s": "σ<sub>S</sub> (excited singlet-state absorption cross-section):",
    "sig_t": "σ<sub>T</sub> (triplet-state absorption cross-section):",
    "sig_s2": "σ<sub>S2</sub> (higher singlet-state cross-section):",
    "sig_t2": "σ<sub>T2</sub> (higher triplet-state cross-section):",
    "t_10": "τ<sub>10</sub> (fluorescence decay time, s):",
    "t_13": "τ<sub>13</sub> (intersystem crossing time, s):",
    "t_21": "τ<sub>21</sub> (excited singlet to lower excited singlet relaxation time, s):",
    "t_30": "τ<sub>30</sub> (phosphorescence decay time, s):",
    "t_43": "τ<sub>43</sub> (triplet excited-state relaxation time, s):",
}

LEGEND_ITEMS: list[str] = [
    "λ: wavelength",
    "σ: absorption cross-section",
    "τ: time constant",
    "w<sub>0</sub>: beam waist",
    "M<sup>2</sup>: beam quality factor",
    "E<sub>pulse</sub>: pulse energy",
]

FIT_PARAM_LABELS: list[str] = [
    "σ<sub>G</sub> (ground-state absorption cross-section)",
    "σ<sub>S</sub> (excited singlet-state absorption cross-section)",
    "σ<sub>T</sub> (triplet-state absorption cross-section)",
    "τ<sub>10</sub> (fluorescence decay time, s)",
    "τ<sub>13</sub> (intersystem crossing time, s)",
    "τ<sub>21</sub> (excited singlet to lower excited singlet relaxation time, s)",
    "τ<sub>30</sub> (phosphorescence decay time, s)",
    "τ<sub>43</sub> (triplet excited-state relaxation time, s)",
]

FITTING_MODE_HELP: dict[str, str] = {
    "Current Data": "Current Data mode uses the latest data from the Data Collection tab.",
    "Single File": "Single File mode expects a CSV with z, ai0, ai1 and a matching TOML sidecar.",
    "Multiple Files": "Multiple Files mode loads multiple CSV+TOML pairs with matching point counts.",
}
