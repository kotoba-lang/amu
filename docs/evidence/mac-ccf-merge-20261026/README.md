# Merged CCF + Mac FS2 native candidate (2026-10-26)

Source revision: `59bcf80c8a822de03ef9d35df14401b35da4611a`. The signed Mac Amu root rebuilt the merged FULL47 source; F1 and F2 emitted the same container. The Mac user gate compiled the actual AIUEOS/FS2 product and verified raw byte roundtrip. The same Mac producer emitted the tracked ARM packed root and x86 full compiler candidates. See `transition.json`, `mac-aiueos-user-target.json`, and `cross.json` for exact identities.

The cross gate did not execute Linux code. Native ARM/x86 fixed points, the full corpus, controller links, public aliases, CCF controls, and exact-head CI remain qualification gates. The prior main CCF qualification is historical evidence for different source and image bytes.
