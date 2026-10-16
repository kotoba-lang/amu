# M104 xgboost tree-depth diagnostic

`profile.json` records deterministic path lengths for the 128 samples and 400
trees in the M104 translated Kotoba port. Reproduce it from the repository root
with:

```sh
python3 docs/evidence/embench-xgboost-depth-20261016/profile.py
```

The profile follows the port's `walk` operation over its decoded byte arrays.
The current `tbat` compiler specialization emits five branch-free walk steps
and keeps a reached leaf in place. For the recorded inputs, the average dynamic
walk is 3.58 steps; 52.6% of walks end before step five. This suggests a
candidate to reduce work after early leaf arrival.

This is only input-data analysis. It does not prove the generated M104 image
takes the `tbat` path for every walk, quantify the cost of the extra loads,
compare branch prediction, or establish a speedup. Any change needs exact
result/fuel evidence and a quiet-host paired xgboost timing before it can be
retained as a performance optimization.
