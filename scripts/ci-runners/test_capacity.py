#!/usr/bin/env python3
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from capacity import decide

ALL = {"amu-linux-arm64", "amu-macos-arm64", "amu-linux-x86_64"}
assert decide("selfhosted", ALL, [3, 20]) == ("selfhosted", "ok")
assert decide("selfhosted", ALL - {"amu-linux-arm64"}, [])[0] == "hosted"       # dead runner pool -> fall back
assert decide("selfhosted-arm", {"amu-linux-arm64"}, [])[0] == "hosted"          # mac pool missing
assert decide("selfhosted-arm", {"amu-linux-arm64", "amu-macos-arm64"}, [500])[0] == "hosted"  # stuck queue
assert decide("selfhosted-arm", set(), [])[0] == "hosted"
assert decide("hosted", set(), [999]) == ("hosted", "not self-hosted")           # never promotes
assert decide("", ALL, [])[0] == ""
print("ok")
