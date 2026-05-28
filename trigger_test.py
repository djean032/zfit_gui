import argparse
import time

import nidaqmx
import numpy as np
from nidaqmx.constants import AcquisitionType, Edge

DEFAULT_DEVICE = "Dev1"
DEFAULT_PFI = "PFI0"
DEFAULT_SAMPLES_PER_READ = 140
DEFAULT_TIMEOUT_S = 5.0
DEFAULT_RATE_HZ = 1_000_000.0
DEFAULT_PRETRIGGER_SAMPLES = 10
DEFAULT_DELAY_US = 0.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trigger-only NI-DAQ acquisition test.")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="DAQ device name, e.g. Dev1")
    parser.add_argument("--pfi", default=DEFAULT_PFI, help="PFI terminal name, e.g. PFI0")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help="Read timeout in seconds",
    )
    parser.add_argument(
        "--delay-us",
        type=float,
        default=DEFAULT_DELAY_US,
        help="Post-trigger delay in microseconds for amplitude readout",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.timeout <= 0:
        raise ValueError("--timeout must be > 0")
    if args.delay_us < 0:
        raise ValueError("--delay-us must be >= 0")

    device = args.device
    ai_channels = [f"{device}/ai0", f"{device}/ai1"]
    trigger_source = f"/{device}/{args.pfi}"
    samples_per_read = DEFAULT_SAMPLES_PER_READ
    pretrigger_samples = DEFAULT_PRETRIGGER_SAMPLES
    rate_hz = DEFAULT_RATE_HZ
    total_samples = samples_per_read + pretrigger_samples
    delay_samples = int(round(args.delay_us * rate_hz / 1_000_000.0))

    print("Starting trigger-only DAQ test")
    print(f"Device: {device}")
    print(f"Trigger terminal: {trigger_source}")
    print(f"Samples/read: {samples_per_read}")
    print(f"Pretrigger samples: {pretrigger_samples}")
    print(f"Delay: {args.delay_us} us ({delay_samples} samples)")
    print("Reporting: max per window")
    print(f"Read timeout: {args.timeout} s")
    print(f"Rate: {rate_hz} Hz")
    print("Mode: internal AI clock + digital reference trigger (pre/post capture)")
    print("Press Ctrl+C to stop.\n")

    with nidaqmx.Task() as task:
        for ch in ai_channels:
            task.ai_channels.add_ai_voltage_chan(ch, min_val=-10.0, max_val=10.0)

        if samples_per_read <= delay_samples:
            raise ValueError(f"Delay exceeds post-trigger capture. Need delay < {samples_per_read} samples, requested {delay_samples}.")
        task.timing.cfg_samp_clk_timing(
            rate=rate_hz,
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=total_samples,
        )
        task.triggers.reference_trigger.cfg_dig_edge_ref_trig(
            trigger_source=trigger_source,
            trigger_edge=Edge.RISING,
            pretrigger_samples=pretrigger_samples,
        )

        count = 0
        while True:
            try:
                task.start()
                data = task.read(number_of_samples_per_channel=total_samples, timeout=args.timeout)
                task.stop()

                ai0 = np.asarray(data[0], dtype=float)
                ai1 = np.asarray(data[1], dtype=float)
                start_idx = pretrigger_samples + delay_samples
                ai0_window = ai0[start_idx:]
                ai1_window = ai1[start_idx:]
                ai0_max = float(ai0_window.max())
                ai1_max = float(ai1_window.max())

                count += 1
                ratio = ai1_max / ai0_max if ai0_max != 0 else float("nan")
                print(f"[{count:06d}] max(ai0,ai1)=({ai0_max: .6f}, {ai1_max: .6f}) V, ratio={ratio: .6f}")

            except KeyboardInterrupt:
                print("\nStopped by user.")
                break
            except Exception as exc:
                try:
                    task.stop()
                except Exception:
                    pass
                print(f"[WARN] Read failed: {exc}")
                time.sleep(0.1)


if __name__ == "__main__":
    main()
