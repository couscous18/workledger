# Policy Pack Spec

Each policy pack contains:

- `policy_pack_id`
- `version`
- `basis`
- `title`
- `description`
- `default_function_class`
- `default_treatment_candidate`
- `rules`

Each rule contains:

- `id`
- `priority`
- `when`
- `decision`
- `explanation`

`when` supports `all` and `any` condition blocks.

Conditions require:

- `feature`
- `op`
- `value` where applicable

Supported operators:

- `eq`
- `neq`
- `contains`
- `in`
- `overlaps`
- `exists`
- `gte`
- `lte`

