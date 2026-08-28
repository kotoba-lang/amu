const sha256 = /^[0-9a-f]{64}$/;

function requireSha256(value, label) {
  if (!sha256.test(value ?? "")) throw new Error(`${label} is not sealed by SHA-256`);
}

export function assessComparatorCoverage(manifest, domains, comparator = "rust") {
  const ids = domains.map(domain => domain.id);
  if (new Set(ids).size !== ids.length)
    throw new Error("comparator evidence contains duplicate domain IDs");
  const requiredIds = manifest.requiredDomains.map(domain => domain.id);
  if (new Set(requiredIds).size !== requiredIds.length)
    throw new Error("manifest contains duplicate required domain IDs");
  const byId = new Map(domains.map(domain => [domain.id, domain]));
  const missingDomains = [];
  const evidence = [];
  const toolVersions = new Set();

  for (const required of manifest.requiredDomains) {
    const domain = byId.get(required.id);
    const engine = domain?.engines?.[comparator];
    if (!domain || !engine) {
      missingDomains.push(required.id);
      continue;
    }
    if (domain.fixture !== required.fixture
        || domain.knownAnswer?.benchmark !== required.knownAnswer)
      throw new Error(`${required.id} comparator benchmark identity drifted`);
    const expected = domain.knownAnswer.result;
    const samples = engine.samples ?? [];
    if (samples.length < 1 || samples.some(sample => sample.result !== expected))
      throw new Error(`${required.id} ${comparator} known-answer rejection`);
    if (!(domain.knownAnswer.verifiedBy ?? []).includes(comparator))
      throw new Error(`${required.id} ${comparator} is not a known-answer verifier`);
    if (domain.contract.rotation !== "all-engine-pairs ABBA/BAAB per run")
      throw new Error(`${required.id} ${comparator} lacks ABBA/BAAB evidence`);
    if (domain.contract.nativeArtifactAbi !== manifest.claimContract.nativeArtifactAbi)
      throw new Error(`${required.id} ${comparator} lacks the common native artifact ABI`);
    const optimization = domain.contract.comparatorBuilds?.[comparator]
      ?? (comparator === "rust" ? domain.contract.rustOptimization : null);
    if (typeof optimization !== "string" || optimization.length < 1)
      throw new Error(`${required.id} ${comparator} optimization contract is missing`);
    requireSha256(domain.artifacts?.[comparator]?.sha256,
      `${required.id} ${comparator} binary`);
    requireSha256(domain.artifacts?.[`${comparator}Source`]?.sha256,
      `${required.id} ${comparator} source`);
    const toolVersion = domain.environment?.[comparator === "rust" ? "rustc" : comparator];
    if (typeof toolVersion !== "string" || toolVersion.length < 1)
      throw new Error(`${required.id} ${comparator} tool version is missing`);
    toolVersions.add(toolVersion);
    evidence.push({
      id: required.id,
      fixture: required.fixture,
      knownAnswer: expected,
      samples: samples.length,
      sourceSha256: domain.artifacts[`${comparator}Source`].sha256,
      binarySha256: domain.artifacts[comparator].sha256,
      toolVersion,
      optimization,
      nativeArtifactAbi: domain.contract.nativeArtifactAbi,
      rotation: domain.contract.rotation,
    });
  }

  if (toolVersions.size > 1)
    throw new Error(`${comparator} tool version changed inside one suite`);
  const complete = missingDomains.length === 0
    && evidence.length === manifest.requiredDomains.length;
  return {
    status: complete ? "complete" : evidence.length === 0 ? "unavailable" : "incomplete",
    requiredDomainCount: manifest.requiredDomains.length,
    measuredDomainCount: evidence.length,
    missingDomains,
    toolVersion: toolVersions.values().next().value ?? null,
    complete,
    evidence,
  };
}
