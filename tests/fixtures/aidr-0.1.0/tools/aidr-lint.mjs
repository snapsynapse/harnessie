#!/usr/bin/env node
// aidr-lint: reference linter for the AIDR specification (SPEC.md).
// Usage: node tools/aidr-lint.mjs <file-or-dir> [...more]
// Exit 0 when every checked file conforms, 1 otherwise.
// No dependencies. Conformance is defined by SPEC.md, not by this tool.

import { collectAidrFiles, lintFile } from './lib/aidr-core.mjs';

const targets = process.argv.slice(2);
if (targets.length === 0) {
  console.error('usage: node tools/aidr-lint.mjs <file-or-dir> [...more]');
  process.exit(2);
}

let failed = false;
for (const target of targets.flatMap(collectAidrFiles)) {
  const { errors, claims } = lintFile(target);
  if (errors.length) {
    failed = true;
    console.log(`FAIL ${target}`);
    for (const e of errors) console.log(`  - ${e}`);
  } else {
    console.log(`PASS ${target}${claims.length ? ` [${claims.join(', ')}]` : ''}`);
  }
}
process.exit(failed ? 1 : 0);
