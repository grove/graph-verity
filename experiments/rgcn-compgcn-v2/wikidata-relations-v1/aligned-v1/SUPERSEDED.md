# Superseded, unscored preregistration

This directory records the initial aligned-v1 preparation. It was not used for
model inference or scored training. Review before execution found that its
preflight wrapper passed the v3 historical manifest to a validator pinned to a
different final manifest, and its inference authorization did not bind a
separate verified local model-asset/runtime receipt.

The v1 manifest, deterministic export, and protocol documents are preserved as
written. The corrected, separately versioned protocol is in
[`../aligned-v2/`](../aligned-v2/). Do not execute commands from this v1
directory.
