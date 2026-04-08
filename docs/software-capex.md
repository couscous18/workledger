# Software CapEx Review

`workledger` can support software accounting review, but that is a downstream use case built on top of the broader agent work ledger.

It takes ledgered software work and turns it into evidence-backed candidate classifications for finance and engineering.

If you are new to the project, start with the [Builder Demo](builder-demo.md). That is the homepage story. This page shows one higher-stakes interpretation layered on top of the same `WorkUnit` foundation.

## The Wedge

- `maintenance_bugfix` maps to `maintenance_non_capitalizable`
- `external_product_development` maps to `capitalize_candidate`
- `internal_use_software` maps to `capitalize_candidate`
- ambiguous or low-evidence work remains review-required

This use case remains valuable because it shows how rollup, evidence, confidence, and review states can support higher-stakes interpretation without pretending the model is always certain.

## Public Artifacts

- [HF bundle README](https://github.com/couscous18/workledger/blob/main/hf/software-capex-review/README.md)
- [Synthetic example dataset](https://raw.githubusercontent.com/couscous18/workledger/main/hf/software-capex-review/dataset/software_capex_review_sample.jsonl)
- [Gradio Space app](https://github.com/couscous18/workledger/blob/main/hf/software-capex-review/space/app.py)
- [Notebook demo](https://github.com/couscous18/workledger/blob/main/hf/software-capex-review/notebook/workledger_capex_demo.ipynb)
