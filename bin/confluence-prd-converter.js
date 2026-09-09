#!/usr/bin/env node
/**
 * Confluence PRD Converter - Node.js Binary Runner
 * Supports MCP server launch, adapter initialization (init), and CLI conversion.
 */

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, "..");

const args = process.argv.slice(2);
const command = args[0];

function printHelp() {
  console.log(`
Confluence PRD Converter (v1.0.0) - Universal AI Agent Skill & FastMCP Server

Usage:
  npx confluence-prd-converter <command> [options]
  npx -y github:hanifalkauni/confluence-prd-converter [options]

Commands:
  --mcp               Start the FastMCP server via stdio JSON-RPC
  init                Install adapter rules for all AI Agent IDEs in the current workspace
  --input, -i <url>   Convert a Confluence page URL, pageId, or local .html export
  --output, -o <path> Output Markdown file path (default: ./prd.md)
  --help, -h          Show this help message

Examples:
  npx -y github:hanifalkauni/confluence-prd-converter --mcp
  npx -y github:hanifalkauni/confluence-prd-converter init
  npx -y github:hanifalkauni/confluence-prd-converter --input "https://wiki.yourcompany.com/pages/viewpage.action?pageId=12345"
  npx -y github:hanifalkauni/confluence-prd-converter --input "./export.html" --output "./prd.md"
`);
}

if (args.includes("--help") || args.includes("-h")) {
  printHelp();
  process.exit(0);
}

if (command === "init") {
  console.log("\n🚀 Initializing Confluence PRD Converter adapters for all AI Agent IDEs...\n");
  const cwd = process.cwd();
  const adaptersDir = join(rootDir, "adapters");
  const targets = [
    { src: join(adaptersDir, "antigravity", "SKILL.md"), dest: join(cwd, ".agents", "skills", "confluence-prd-converter", "SKILL.md") },
    { src: join(adaptersDir, "claude", "CLAUDE.md"), dest: join(cwd, "CLAUDE.md") },
    { src: join(adaptersDir, "cursor", "confluence-prd-converter.mdc"), dest: join(cwd, ".cursor", "rules", "confluence-prd-converter.mdc") },
    { src: join(adaptersDir, "windsurf", "windsurfrules.md"), dest: join(cwd, ".windsurf", "rules", "confluence-prd-converter.md") },
    { src: join(adaptersDir, "cline", "clinerules.md"), dest: join(cwd, ".clinerules", "confluence-prd-converter.md") },
    { src: join(adaptersDir, "copilot", "copilot-instructions.md"), dest: join(cwd, ".github", "copilot-instructions.md") },
    { src: join(adaptersDir, "kiro", "steering.md"), dest: join(cwd, ".kiro", "steering", "confluence-prd-converter.md") },
    { src: join(adaptersDir, "continue", "prompt.md"), dest: join(cwd, ".continue", "rules", "confluence-prd-converter.md") }
  ];

  let installed = 0;
  for (const t of targets) {
    if (fs.existsSync(t.src)) {
      fs.mkdirSync(dirname(t.dest), { recursive: true });
      fs.copyFileSync(t.src, t.dest);
      console.log(`  ✓ Installed: ${t.dest.replace(cwd, ".")}`);
      installed++;
    }
  }

  console.log(`\n✨ Successfully initialized ${installed} agent adapters! You can now use @confluence-prd-converter across any AI IDE.\n`);
  process.exit(0);
}

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
