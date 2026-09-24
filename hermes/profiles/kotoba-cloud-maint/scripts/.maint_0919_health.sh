for p in / /en/ /health /404-page /docs/ /twin/; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -L "https://kotoba.cloud$p")
  echo "kotoba.cloud$p -> $code"
done
curl -s https://kotoba.cloud/health | head -c 200; echo
code=$(curl -s -o /dev/null -w '%{http_code}' https://api.kotoba.cloud/v1/control-plane)
echo "api control-plane -> $code"
random=$(curl -s -o /dev/null -w '%{http_code}' "https://kotoba.cloud/zzz-maint-$$")
echo "random path -> $random"
