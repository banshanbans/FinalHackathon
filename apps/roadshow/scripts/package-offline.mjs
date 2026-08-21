import { chmod, cp, mkdir, rm, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { execFileSync } from "node:child_process";

const root = resolve(import.meta.dirname, "..");
const output = join(root, "offline-dist");
const build = join(root, ".offline-build");
await rm(output, { recursive: true, force: true });
await rm(build, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await mkdir(build, { recursive: true });

const arm = join(build, "server-arm64");
const intel = join(build, "server-x64");
const moduleCache = join(build, "module-cache");
await mkdir(moduleCache, { recursive: true });
const swiftEnvironment = { ...process.env, CLANG_MODULE_CACHE_PATH: moduleCache, SWIFT_MODULECACHE_PATH: moduleCache };
execFileSync("swiftc", [join(root, "offline/server.swift"), "-O", "-target", "arm64-apple-macos13", "-module-cache-path", moduleCache, "-o", arm], { stdio: "inherit", env: swiftEnvironment });
execFileSync("swiftc", [join(root, "offline/server.swift"), "-O", "-target", "x86_64-apple-macos13", "-module-cache-path", moduleCache, "-o", intel], { stdio: "inherit", env: swiftEnvironment });
const universal = join(build, "13110-server");
execFileSync("lipo", ["-create", arm, intel, "-output", universal]);

const packages = [
  { id: "mac-universal", start: "start-mac.command" },
  { id: "windows-x64", start: "start-windows.bat" },
];
for (const item of packages) {
  const name = `13110-离线演示-${item.id}`;
  const directory = join(output, name);
  await mkdir(directory, { recursive: true });
  await cp(join(root, "dist/client"), join(directory, "site"), { recursive: true });
  await cp(join(root, "offline/README-演示说明.txt"), join(directory, "README-演示说明.txt"));
  if (item.id === "mac-universal") {
    await cp(universal, join(directory, "13110-server"));
    await cp(join(root, "offline/start-mac.command"), join(directory, "启动13110.command"));
    await chmod(join(directory, "13110-server"), 0o755);
    await chmod(join(directory, "启动13110.command"), 0o755);
  } else {
    await cp(join(root, "offline/server-windows.ps1"), join(directory, "server-windows.ps1"));
    await cp(join(root, "offline/start-windows.bat"), join(directory, "启动13110.bat"));
  }
  execFileSync("ditto", ["-c", "-k", "--keepParent", directory, join(output, `${name}.zip`)]);
}
const archives = packages.map(({ id }) => join(output, `13110-离线演示-${id}.zip`));
const shasum = execFileSync("shasum", ["-a", "256", ...archives], { encoding: "utf8" });
await writeFile(join(output, "SHA256.txt"), shasum);
console.log(`Offline packages ready: ${output}`);
