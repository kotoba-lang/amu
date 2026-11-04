# WP02 monitor request binding

The experimental monitor previously stored only phase, sequence and clock
values. A caller could accidentally present a different valid request and a
matching frame after readiness; the state did not bind the earlier request.
On the local Darwin ARM64 diagnostic, the old selected native source accepted
a heartbeat for a separately constructed request with a different token after
readiness for the original request. An initial probe accidentally mutated
the same vector and was not valid evidence; the recorded before fixture uses
two distinct request vectors.

The candidate adds `darwin-watch-monitor-start` and stores the exact 32-byte
request after the five numeric state fields. Each step checks equality before
processing; old five-field states and invalid starts return unknown. This
changes the experimental state layout and requires callers to start fresh;
there is no migration of an in-flight monitor. Copying the request is
correlation, not authentication: the trusted host must protect state and
bind it to the launched watcher and process.

The updated selected-source native fixture passed on one local Mac with the
pinned diagnostic compiler and FS2 packager. It exercised valid readiness,
heartbeat, poll and exit; cross-request heartbeat, poll and exit refusals;
invalid starts, old-state refusal and existing clock/sequence cases. A
guard-bypass mutant that retained the length check but ignored request bytes
failed; an existing clock rollback mutant also failed. Each compiler and
native process had a three-second CPU cap, with no hard memory cap. This is a
pure state-machine fixture: no real watcher, authenticated host supervisor,
process tree or governor ran. The CLI product test driver declaration was
updated and its Python syntax checked, but the full CLI product test was not
run here.

The old source and cases SHA-256 values were
`1cbcbfe1e4a33e82fe010fd586ffcabf58cb809e2ebf0fc7879545e5750bfbf0` and
`4506cce36c7e1093ee4a8a645965432e2480a7b6ed77478d75a99c0323fe38b4`.
The before source-unity and signed image values were
`453dc57cf37873c68c7a3cdb2d061788bdde8c22e8150057163542dbf194c169` and
`96bcacb9a44ae9606227c7e798b74f80f73e4dcff052457183c7977c3445bb47`.
The updated source and cases hashes were
`e6ead3473202d9b3e916a045bca8a516e096458801bf6c1825e77aceb726216c` and
`e72b057217982e8aede6ff3fa39400302fa732dc9fbc1fd890cd146d2ff030f2`.
The after source-unity and signed image values were
`fe3970a4e410b49f15c0dee04fa6e99f1af7bfc8f51cf81e86761ecc647001a7` and
`43487623fe58cebc4aa28e60fbe1636b8c7356527d6c939b58b60131b3cc495a`;
the cross-request guard mutant image was
`18d2be465eca06d878a9008ade6d9c494f8d0fa5fa8373cf874881c80a884b9a`.

`before.py` and `after.py` are the exact task-specific operators, hashes
`6c22e09455c6a7ec7979783e1af92b38b140df5d681634519c3105b55965c879` and
`73437fdf9a191552fcd1973911118c3f0a84580500a0d64ec60c96901878faca`.
They reference local paths and retain temporary build directories; they are
evidence rather than unattended operations. The original source and cases
must be restored to the named temporary paths for `before.py`, and the
separately pinned compiler and packager from the existing watcher evidence
are required. This does not qualify selfhost, the real host or the governor.

## Recorded WP02 frame replay

A separate local run of the signed experimental WP02 watcher observed an
owned four-second `/bin/sleep` child. The test captured readiness, three
heartbeats, twelve empty polls and exit, with monotonic timestamps from the
Python observer. The watcher and child exited successfully. A newly compiled
and signed selected-source native fixture initialized the request-bound state
and replayed those 17 events and recorded timestamps successfully. The
watcher SHA-256 was
`1fdff12c551e847948096c96bf4037d91aee540310ca9947f43c9dda20d3869b`;
the replay source and signed image SHA-256 values were
`dcba9dd9e4a60adc2302b2c52bd8a269b8af7ae342031048af73546c66283a2f` and
`192c78cbd83679f804ae77e6911385340ff03a3977a7f58f17c258f24f74a47a`.
The recorded elapsed time was 4,011 ms. The observer and compiler/fixture
processes had a three-second CPU cap; no hard memory cap was imposed.

The exact captured `replay.kotoba`, `replay-capture.py` and `replay-build.py`
are archived here. Their SHA-256 values are respectively the source hash
above, `8688fd6bf0e3fc7061b656cdd0fae4a81745be2305617db5e28b5514d11abbdf`,
and `bb2135646eeb3b6dd555547a3466e2ba7c4039bdf63fcbff02efa409768933dd`.
The scripts use task-specific absolute paths and the builder retains a
temporary directory. This is offline replay of actual diagnostic frames and
times, not live enforcement by the monitor, a trusted supervisor, process
containment or resource-governor qualification.
