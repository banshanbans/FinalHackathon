#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const requested = process.argv[2];
const target = requested ? path.resolve(root, requested) : path.join(root, "src");
const sourceForbidden = [
  /apps\/(presentation|web)/,
  /(?:^|["'`])\/api(?:\/|["'`])/,
  /https?:\/\//,
  /VITE_API/,
];
const builtForbidden = [
  /apps\/(presentation|web)/,
  /(?:^|["'`])\/api(?:\/|["'`])/,
  /VITE_API/,
  /eoimages\.gsfc\.nasa\.gov/,
  /visibleearth\.nasa\.gov/,
];
const forbidden = requested ? builtForbidden : sourceForbidden;
const extensions = new Set([".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".json"]);

function filesUnder(directory) {
  if (!existsSync(directory)) throw new Error(`Boundary target missing: ${directory}`);
  if (statSync(directory).isFile()) return [directory];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const child = path.join(directory, entry.name);
    return entry.isDirectory() ? filesUnder(child) : [child];
  });
}

const violations = [];
for (const file of filesUnder(target)) {
  if (!extensions.has(path.extname(file))) continue;
  const content = readFileSync(file, "utf8");
  for (const pattern of forbidden) {
    if (pattern.test(content)) violations.push(`${path.relative(root, file)} matches ${pattern}`);
  }
}

if (violations.length) {
  console.error(violations.join("\n"));
  process.exit(1);
}
console.log(`Roadshow boundary check passed: ${path.relative(root, target) || "."}`);
