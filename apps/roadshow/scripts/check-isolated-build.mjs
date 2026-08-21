#!/usr/bin/env node
import { cpSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const temporaryRoot = mkdtempSync(path.join(tmpdir(), "policyscope-roadshow-isolated-"));
const copy = path.join(temporaryRoot, "roadshow");

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: copy,
    env: { ...process.env, npm_config_cache: path.join(root, ".npm-cache") },
    encoding: "utf8",
    stdio: "pipe",
  });
  if (result.status !== 0) {
    process.stderr.write(result.stdout ?? "");
    process.stderr.write(result.stderr ?? "");
    process.exitCode = result.status ?? 1;
    throw new Error(`${command} ${args.join(" ")} failed`);
  }
  process.stdout.write(result.stdout ?? "");
}

try {
  cpSync(root, copy, {
    recursive: true,
    filter: (source) => !["node_modules", "dist", ".npm-cache", "test-results", "playwright-report"].includes(path.basename(source)),
  });
  run("npm", ["ci", "--prefer-offline", "--no-audit", "--no-fund"]);
  run("npm", ["run", "build"]);
  console.log("Isolated roadshow build passed.");
} finally {
  rmSync(temporaryRoot, { recursive: true, force: true });
}
