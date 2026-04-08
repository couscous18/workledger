# Extension Guidance

Use namespaced extension facets to attach domain-specific context without expanding the core schema.

Recommended namespaces:

- `git`
- `marketing`
- `support`
- `finance`
- `vendor`

Example:

```json
{
  "git": {
    "repository": "product-api",
    "branch": "fix/bug-142-timeouts"
  }
}
```

