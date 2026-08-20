#!/usr/bin/env node
// PostToolUse hook: warns early if an edited file under _articles/ is missing
// `status: ready` in its frontmatter, mirroring the check in
// .github/workflows/pages.yml so the problem is visible before CI runs.
// No dependencies beyond Node's standard library.
//
// Reads stdin asynchronously (not fs.readFileSync(0)) because synchronous
// reads from a piped stdin fd are unreliable on Windows/Git Bash and were
// observed to silently return empty output during local testing.

const fs = require("fs");

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", () => resolve(data));
  });
}

async function main() {
  const raw = await readStdin();
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const filePath =
    (payload.tool_input && (payload.tool_input.file_path || payload.tool_input.path)) || "";
  const normalized = filePath.replace(/\\/g, "/");

  if (!/(^|\/)_articles\/[^/]+\.md$/.test(normalized)) {
    process.exit(0);
  }

  let content;
  try {
    content = fs.readFileSync(filePath, "utf8");
  } catch {
    process.exit(0);
  }

  const hasReadyStatus = /^status:\s*ready\s*$/m.test(content);
  if (!hasReadyStatus) {
    process.stderr.write(
      `_articles/ 配下の記事に "status: ready" が見つかりません: ${filePath}\n` +
        `_articles/ には status: ready の記事のみを置く運用です` +
        `(.github/workflows/pages.yml のCIチェックと同じ基準)。\n` +
        `この警告を消すために自分で status: ready へ書き換えないこと。status変更はオーナー承認が` +
        `必要な操作(CLAUDE.md/docs/publish-checklist.md)。オーナーに確認するか、readyになるまで` +
        `_articles/ 以外の場所で作業すること。\n`
    );
    process.exit(2);
  }

  process.exit(0);
}

main();
