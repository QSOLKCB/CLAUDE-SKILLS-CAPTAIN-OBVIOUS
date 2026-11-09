---
name: no-ghosts-in-the-tick
description: Record and verify SHA-256 file baselines during visual-only game changes, while requiring separate simulations to establish deterministic tick parity.
---

# No Ghosts in the Tick

**Mission:** detect changes to authoritative fixtures, traces, and state snapshots while visual code gets a makeover.

## Use when
- A rendering or UI refactor promises unchanged simulation output.
- A reproducibility experiment needs a content baseline.
- Someone claims all ten cabinets are deterministic but offers only a green badge.

## Procedure
1. Run baseline simulations **before** editing, fixing seeds, inputs, ticks and tool versions. Save authoritative output snapshots.
2. Pin those snapshot files using:

       python3 tools/obvious.py pin write --root . --manifest /tmp/captain-pins.json tests/test_obvious.py

   Replace the sample file with the **real simulation output files** to test byte parity.
3. After the refactor, rerun the same simulations and regenerate the same output paths.
4. Verify:

       python3 tools/obvious.py pin verify --root . --manifest /tmp/captain-pins.json

5. Interpret PASS as **byte parity of listed files**, not overall simulation correctness.
6. Record fixture generation commands, seeds, input tapes, tick counts and actual test outcomes alongside the pins.

## Utility contract
- Writes a sorted JSON manifest with schema version and SHA-256 digests.
- Refuses traversal, absolute input paths, symlinked inputs or manifest path components, duplicate paths and manifest self-inclusion (including hard-linked aliases of an existing manifest).
- Replaces the manifest atomically on the same filesystem.
- Fails verification on changed bytes or malformed manifests.
- Does not measure frame rate, inspect render purity, or guarantee snapshots were properly generated.

## Captain's report
> "Our pixels have been promoted. The simulation has not been invited to the ceremony."

**Important:** file parity is one independently checkable component of a deterministic 60 FPS claim, not proof of tick behaviour.