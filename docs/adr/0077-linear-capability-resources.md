# ADR 0077: linear capability resources

- Status: Accepted
- Date: 2026-07-26

`compile-component --capability-mode linear-resource` lowers a qualified direct
scalar capability call to a WIT resource contract:

```wit
resource now-capability;
issue-now: func() -> own<now-capability>;
execute-now: func(cap: own<now-capability>, request: s64) -> s64;
```

The generated core module calls `issue-now` and immediately moves the returned
handle into `execute-now`. The Component Model canonical ABI therefore owns the
move; a copied integer is not a second capability. The compiler rejects general
control flow in this mode until its lowering can preserve the same move.

Function-shaped capability imports remain a compatibility profile. Artifacts
record `:capability-mode`, so admission cannot silently treat them as linear.
