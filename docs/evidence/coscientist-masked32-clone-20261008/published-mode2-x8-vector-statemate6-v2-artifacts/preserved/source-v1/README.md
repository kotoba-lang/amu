# SOURCE-only vector/statemate six-call registration

Review `preregistration.json`, `CONTRACT.md`, `run.py`, `launch-wrapper.py` and pure controls before root GO. No GO is supplied. Pure controls involve only normal file reads and injected bytes; no Popen/thread/FD/process/resource/group/kernel APIs are called. Candidate stage HOLD persists even if compiler artifacts complete.

The pinned interpreter may later run `run.py` with one exact root GO path, after two exact SOURCE reviews. Four commands compile/extract the same synthetic vector fixture using OFF and ON; two compile/extract original unchanged statemate using ON. No native guests or timing.
