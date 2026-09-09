#!/usr/bin/env node
/**
 * Confluence PRD Converter - Node.js Binary Runner
 * Spawns the FastMCP server or CLI runner in Python
 */

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, "..");

const args = process.argv.slice(2);

let pythonScript;
let scriptArgs = [];

if (args.includes("--mcp") || args.length === 0) {
  pythonScript = join(rootDir, "server.py");
} else {
  pythonScript = join(rootDir, "scripts", "run_converter.py");
  scriptArgs = args;
}

const child = spawn("python", [pythonScript, ...scriptArgs], {
  stdio: "inherit",
  env: process.env,
  cwd: rootDir
});

child.on("error", (err) => {
  console.error("Failed to start Python subprocess:", err);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
