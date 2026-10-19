// Post-render: remove drafts from the built site entirely.
//
// `draft-mode: gone` blanks a draft's HTML but Quarto still copies its images and figure
// output into _site/, so they deploy to gh-pages. For every rendered page that is a blank
// draft stub AND whose source has `draft: true`, delete the page — and for posts/<slug>/,
// the whole directory. Under the `drafts` profile (draft-mode: visible) drafts render in
// full, are not stubs, and are left alone, so preview is unaffected.

const outDir = Deno.env.get("QUARTO_PROJECT_OUTPUT_DIR") ?? "_site";
const STUB = /^\s*<!DOCTYPE html>\s*<html[^>]*>\s*<\/html>\s*$/i;

function sourceIsDraft(rel: string): boolean {
  const base = rel.replace(/\.html$/, "");
  for (const ext of [".qmd", ".ipynb", ".md"]) {
    let text: string;
    try {
      text = Deno.readTextFileSync(base + ext);
    } catch {
      continue;
    }
    if (ext === ".ipynb") {
      const src = JSON.parse(text).cells?.[0]?.source ?? "";
      text = Array.isArray(src) ? src.join("") : src;
    }
    const yaml = text.match(/^---\n([\s\S]*?)\n---/);
    return !!yaml && /^draft:\s*true\s*$/m.test(yaml[1]);
  }
  return false;
}

function* htmlFiles(dir: string): Generator<string> {
  for (const e of Deno.readDirSync(dir)) {
    const p = `${dir}/${e.name}`;
    if (e.isDirectory && e.name !== "site_libs") yield* htmlFiles(p);
    else if (e.isFile && e.name.endsWith(".html")) yield p;
  }
}

const pruned: string[] = [];
for (const file of [...htmlFiles(outDir)]) {
  if (Deno.statSync(file).size > 500 || !STUB.test(Deno.readTextFileSync(file))) continue;
  const rel = file.slice(outDir.length + 1);
  if (!sourceIsDraft(rel)) continue;
  const post = rel.match(/^posts\/([^/]+)\/index\.html$/);
  const target = post ? `${outDir}/posts/${post[1]}` : file;
  Deno.removeSync(target, { recursive: true });
  pruned.push(post ? `posts/${post[1]}/` : rel);
}
if (pruned.length) console.log(`prune-drafts: removed ${pruned.length} draft(s): ${pruned.join(", ")}`);
