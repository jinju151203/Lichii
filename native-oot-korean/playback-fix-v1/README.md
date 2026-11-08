# Controller Ocarina playback fix

Controller-driven playback can terminate at `nn::hid::IsOunceVibrationDeviceMounted` with `FATAL: sm: service "hid" is not implemented`. The runtime patch routes both public and detail mount queries through the existing host vibration-device mapping.

`Ocarina_Playback_Fix.exe` applies only this runtime source change to the existing installation, backs up its source and executable, and rebuilds with the already installed tools. It verifies real PE host-table entries before reporting success and rolls back on build or verification failure. It does not modify saves, language or graphics settings.

Apply `ocarina-controller-playback-hid-v1.patch` to an Ocarina Recomp source checkout, then rebuild the runtime and executable normally. The patch is independent of the prior Korean menu/launcher overlays. The helper sources and tests are included here; `make_playback_fix.py` runs from the full Ocarina Recomp checkout.

Validated: real HID handler ABI/controller-state tests, Windows x64 cross-compilation, backup/idempotence/rollback tests, actual linked PE host-table inspection, PowerShell parse, and packaged resource integrity. Real gameplay remains unverified.

Game-free helper EXE: 60416 bytes, SHA-256 `0691354fcc0c7d6ab3f549f48d6f54b046fa648eedc26df8477988d353632305`.
