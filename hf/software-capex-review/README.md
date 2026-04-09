# workledger software capex review bundle

This bundle is a downstream example package for `workledger`, an open trace-to-work layer for AI systems.

The core thesis comes first: noisy AI traces in, reviewable `WorkUnit`s out.

Software capex review is one interpretation layered on top of that primitive. The thing to notice first is the shape of the output:

- raw spans become work units
- work units get policy-backed classifications
- ambiguous items remain in a review queue

If you want the flagship public story first, open the repo's [builder demo page](../../docs/builder-demo.md).

This bundle is centered on the software capex review wedge:

- maintenance bugfixes
- external product development
- internal-use software
- ambiguous review-required work

## Contents

- `dataset/software_capex_review_sample.jsonl` synthetic example data
- `space/app.py` Gradio Space app
- `notebook/workledger_capex_demo.ipynb` notebook walkthrough
- `runtime.py` shared evaluation helpers

## Publication Notes

The bundle is designed as a starting point you can copy into Hugging Face assets and adapt after the broader repo story is clear.

- Use the `space/` directory for a Space.
- Use the `dataset/` directory for a Hub dataset repo.
- Use the `notebook/` directory for a walkthrough notebook or Hub notebook asset.

The bundled sample data is synthetic and aligned to the built-in management reporting policy pack so the public demo can show a finance-facing downstream story without exposing private traces.

Treat this bundle as example packaging, not as an independently validated benchmark.
