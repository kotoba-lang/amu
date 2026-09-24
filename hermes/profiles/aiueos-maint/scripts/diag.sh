#!/bin/bash
exec 2>&1
echo "===START==="
pwd
which gh
gh run list -R kotoba-lang/aiueos --limit 10
echo "gh_exit=$?"
