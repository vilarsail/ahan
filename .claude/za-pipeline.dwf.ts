// za（杂阿含经）1-50 卷流水线：校对(check-ahan) → 修复(fix-ahan) → 导读+词语注释(read-ahan)
// 用法：CreateWorkflow 传 path 指向本文件，max_concurrency=3（实测经验值，4 会触发并发拒绝）。
// 卷内三阶段严格串行；跨卷流水并行；文件级幂等可断点续跑。
// 状态文件：.claude/run-za-pipeline.md（每卷完成自动刷新）。

const BOOK = "za";
const START = 1;
const END = 50;

interface VolumeStat {
  volume: number;
  checkIssues: number;
  fixed: number;
  rejected: number;
  terms: number;
  status: string;
  note: string;
}

interface BatchTask {
  name: string;
  skill: string;
  kind: string;
  inPath: string;
  outPath: string;
}

const VOLS: number[] = [];
for (let n = START; n <= END; n++) VOLS.push(n);

artifact.table("za-progress", {
  title: "za 流水线逐卷进度",
  key: "volume",
  columns: [
    { field: "volume", label: "卷" },
    { field: "checkIssues", label: "校对问题" },
    { field: "fixed", label: "已修复" },
    { field: "terms", label: "注释词条" },
    { field: "status", label: "状态" },
    { field: "note", label: "备注" },
  ],
});

function statValue(out: string, key: string): number {
  const m = out.match(new RegExp(key + "=(\\d+)"));
  return m ? parseInt(m[1]) : -1;
}

async function exists(path: string): Promise<boolean> {
  return (await files.glob(path)).length > 0;
}

async function countIn(path: string, pattern: string): Promise<number> {
  try {
    const text = await files.read(path);
    return (text.match(new RegExp(pattern, "gm")) || []).length;
  } catch (e) {
    return 0;
  }
}

async function runPy(args: string[], what: string): Promise<string> {
  const r = await world.run("python3", args);
  if (r.exitCode !== 0) {
    throw new Error(what + " 失败(exit " + r.exitCode + ")：" + ((r.stderr || "") + (r.stdout || "")).slice(-400));
  }
  return r.stdout;
}

function promptFor(t: BatchTask): string {
  if (t.kind === "导读与词语注释") {
    return "读取 .claude/skills/" + t.skill + "/AGENT_INSTRUCTIONS.md 获取导读与词语注释生成指令，按其要求撰写。\n\n输入文件：" + t.inPath + "\n输出文件：" + t.outPath;
  }
  if (t.skill === "fix-ahan") {
    return "读取 .claude/skills/" + t.skill + "/AGENT_INSTRUCTIONS.md 获取修复判断指令，按其要求判断并改写。\n\n批次文件：" + t.inPath + "\n输出文件：" + t.outPath;
  }
  return "读取 .claude/skills/" + t.skill + "/AGENT_INSTRUCTIONS.md 获取校对指令，按其要求校对。\n\n批次文件：" + t.inPath + "\n输出文件：" + t.outPath;
}

async function runOne(t: BatchTask): Promise<void> {
  try {
    const a = agent(t.name);
    await a.ask(promptFor(t));
  } catch (e) {
    // 子代理失败由输出缺失检测 + 补派兜底
  }
}

// 并行派发全部批次；两轮内对缺失输出的任务补派；仍缺则抛错
async function dispatchAll(tasks: BatchTask[]): Promise<void> {
  await Promise.all(tasks.map(runOne));
  for (let round = 1; round <= 2; round++) {
    const missing: BatchTask[] = [];
    for (const t of tasks) {
      if (!(await exists(t.outPath))) missing.push(t);
    }
    if (missing.length === 0) return;
    log("补派 " + missing.length + " 个未产出结果的任务：" + missing.map(t => t.name).join("、"));
    await Promise.all(missing.map(t => runOne({ name: t.name + "·重试" + round, skill: t.skill, kind: t.kind, inPath: t.inPath, outPath: t.outPath })));
  }
  const still: string[] = [];
  for (const t of tasks) {
    if (!(await exists(t.outPath))) still.push(t.name);
  }
  if (still.length > 0) throw new Error("重试两轮后仍无输出：" + still.join("、"));
}

async function checkStage(n: number): Promise<{ issues: number; skipped: boolean }> {
  if (await exists(BOOK + "/split/" + n + ".check.md")) {
    return { issues: await countIn(BOOK + "/split/" + n + ".check.md", "^### 段落 "), skipped: true };
  }
  await runPy([".claude/skills/check-ahan/prepare_check.py", BOOK, String(n)], "卷" + n + " prepare_check");
  const batchPaths = (await files.glob(BOOK + "/split/check_" + n + "_batch*.json")).sort();
  if (batchPaths.length === 0) throw new Error("卷" + n + " 未生成校对批次文件");
  const tasks: BatchTask[] = batchPaths.map(p => {
    const k = p.match(/batch(\d+)\.json$/);
    return {
      name: "校对·卷" + n + "·批" + (k ? k[1] : String(batchPaths.indexOf(p))),
      skill: "check-ahan",
      kind: "校对",
      inPath: p,
      outPath: p.replace(/check_(\d+)_batch(\d+)\.json$/, "issues_$1_batch$2.json"),
    };
  });
  await dispatchAll(tasks);
  let rep = await runPy([".claude/skills/check-ahan/build_report.py", BOOK, String(n)], "卷" + n + " build_report");
  const failedBatches: number[] = [];
  for (const m of rep.matchAll(/BATCH_FAILED vol=\d+ batch=(\d+)/g)) failedBatches.push(parseInt(m[1]));
  if (failedBatches.length > 0) {
    log("卷" + n + " 有 " + failedBatches.length + " 个校对批次产物无法解析，重新派发");
    const redo: BatchTask[] = failedBatches.map(k => ({
      name: "校对·卷" + n + "·批" + k + "·重建",
      skill: "check-ahan",
      kind: "校对",
      inPath: BOOK + "/split/check_" + n + "_batch" + k + ".json",
      outPath: BOOK + "/split/issues_" + n + "_batch" + k + ".json",
    }));
    await dispatchAll(redo);
    rep = await runPy([".claude/skills/check-ahan/build_report.py", BOOK, String(n)], "卷" + n + " build_report(重建后)");
  }
  return { issues: statValue(rep, "issues"), skipped: false };
}

async function fixStage(n: number): Promise<{ fixed: number; rejected: number; skipped: boolean }> {
  if (await exists(BOOK + "/split/" + n + ".fix.md")) {
    return {
      fixed: await countIn(BOOK + "/split/" + n + ".fix.md", "✅ 已修复"),
      rejected: await countIn(BOOK + "/split/" + n + ".fix.md", "❌ 不成立"),
      skipped: true,
    };
  }
  const out = await runPy([".claude/skills/fix-ahan/prepare_fix.py", BOOK, String(n)], "卷" + n + " prepare_fix");
  if (statValue(out, "issues") <= 0) {
    return { fixed: 0, rejected: 0, skipped: true }; // 校对无问题，无需修复
  }
  const batchPaths = await files.glob(BOOK + "/split/fix_" + n + "_batch*.json");
  const tasks: BatchTask[] = [];
  for (const p of batchPaths.sort()) {
    if (p.endsWith(".verdict.json")) continue;
    const k = p.match(/batch(\d+)\.json$/);
    tasks.push({
      name: "修复·卷" + n + "·批" + (k ? k[1] : String(tasks.length + 1)),
      skill: "fix-ahan",
      kind: "修复判断",
      inPath: p,
      outPath: p.replace(/\.json$/, ".verdict.json"),
    });
  }
  await dispatchAll(tasks);
  const rep = await runPy([".claude/skills/fix-ahan/apply_fix.py", BOOK, String(n)], "卷" + n + " apply_fix");
  const v = await world.run("python3", [".claude/skills/fix-ahan/verify_fix.py", BOOK, String(n)]);
  if (v.exitCode !== 0) {
    log("⚠ 卷" + n + " verify_fix 发现不一致，详见 " + BOOK + "/split/" + n + ".fix.md");
  }
  return { fixed: statValue(rep, "accepted"), rejected: statValue(rep, "rejected"), skipped: false };
}

async function readStage(n: number): Promise<{ terms: number; skipped: boolean }> {
  if (await exists(BOOK + "/split/" + n + ".guide.md") && await exists(BOOK + "/split/" + n + ".notes.md")) {
    return { terms: await countIn(BOOK + "/split/" + n + ".notes.md", "^[①-㊿] "), skipped: true };
  }
  await runPy([".claude/skills/read-ahan/prepare_reading.py", BOOK, String(n)], "卷" + n + " prepare_reading");
  await dispatchAll([{
    name: "导读注释·卷" + n,
    skill: "read-ahan",
    kind: "导读与词语注释",
    inPath: BOOK + "/split/reading_" + n + "_orig.txt",
    outPath: BOOK + "/split/notes_" + n + ".json",
  }]);
  let lastErr = "";
  for (let attempt = 1; attempt <= 3; attempt++) {
    const r = await world.run("python3", [".claude/skills/read-ahan/build_reading.py", BOOK, String(n), String(n)]);
    if (r.exitCode === 0) {
      return { terms: statValue(r.stdout, "placed"), skipped: false };
    }
    lastErr = ((r.stderr || "") + "\n" + (r.stdout || "")).trim();
    if (attempt === 3) break;
    const fixer = agent("修正·导读注释·卷" + n + "·第" + attempt + "轮");
    await fixer.ask("文件 " + BOOK + "/split/notes_" + n + ".json 的构建校验失败，错误信息：\n" + lastErr.slice(-1500) + "\n\n读取 .claude/skills/read-ahan/AGENT_INSTRUCTIONS.md 了解 guide/terms 的格式要求，然后修正该 JSON 文件并写回原路径（只修出错词条或字段，其余内容保持不变）。");
  }
  throw new Error("卷" + n + " 导读注释构建失败：" + lastErr.slice(-300));
}

const CLEANUP_PY = `import glob, os, sys
book, n = sys.argv[1], sys.argv[2]
pats = ["pairs_%s.json" % n, "check_%s_batch*.json" % n, "issues_%s_batch*.json" % n,
        "fix_%s_pairs.json" % n, "fix_%s_batch*.json" % n, "fix_%s_batch*.verdict.json" % n,
        "reading_%s_orig.txt" % n, "notes_%s.json" % n]
removed = 0
for pat in pats:
    for p in glob.glob(os.path.join(book, "split", pat)):
        os.remove(p)
        removed += 1
print("CLEANED vol=%s removed=%d" % (n, removed))`;

const STATUS_PY = `import glob, os, re, sys
from datetime import datetime
book = sys.argv[1]
BOOK_NAMES = {"chang": "长阿含经", "zhong": "中阿含经", "za": "杂阿含经", "zengyi": "增一阿含经"}
name = BOOK_NAMES.get(book, book)
root = os.path.join(book, "split")
CIRCLED = [chr(0x2460 + i) for i in range(20)] + [chr(0x3251 + i) for i in range(15)] + [chr(0x32B1 + i) for i in range(15)]
files = sorted([p for p in glob.glob(os.path.join(root, "[0-9]*.md")) if re.search(r"/([1-9]\\d*)\\.md$", p)],
               key=lambda p: int(re.search(r"/(\\d+)\\.md$", p).group(1)))
rows = []
d1 = d2 = d3 = 0
ti = tf = tt = 0
for p in files:
    n = int(re.search(r"/(\\d+)\\.md$", p).group(1))
    def has(suffix, nn=n):
        return os.path.exists(os.path.join(root, "%d%s" % (nn, suffix)))
    def cnt(path, pat):
        try:
            return len(re.findall(pat, open(path, encoding="utf-8").read(), re.M))
        except Exception:
            return 0
    c, f, g, nt = has(".check.md"), has(".fix.md"), has(".guide.md"), has(".notes.md")
    issues = cnt(os.path.join(root, "%d.check.md" % n), r"^### 段落 ") if c else 0
    fixed = cnt(os.path.join(root, "%d.fix.md" % n), r"✅ 已修复") if f else 0
    terms = cnt(os.path.join(root, "%d.notes.md" % n), r"^[" + "".join(CIRCLED) + r"] ") if nt else 0
    if g and nt:
        d3 += 1
    elif f or (c and issues == 0):
        d2 += 1
    elif c:
        d1 += 1
    ti += issues; tf += fixed; tt += terms
    rows.append("| %d | %s | %s | %s | %d | %d | %d |" % (
        n, "✓" if c else "—", "✓" if (f or (c and issues == 0)) else "—",
        "✓" if (g and nt) else "—", issues, fixed, terms))
total = len(files)
out = []
out.append("# %s %d-%d 流水线运行状态（校对→修复→导读注释）" % (name, 1, total))
out.append("")
out.append("每卷三阶段顺序执行；不同卷之间错级并行。子代理并发上限 L=3（chang 时期实测：7并发挂4、4并发挂1、3并发全成功；2026-10-04 za 卷25 复测 4 并发同样被拒 1 个，维持 L=3）。")
out.append("")
out.append("- 更新时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
out.append("- 三阶段完成：%d 卷；仅校对/修复完成：%d 卷；未完成：%d 卷" % (d3, d1 + d2, total - d1 - d2 - d3))
out.append("- 合计：校对问题 %d 段、已修复 %d 段、注释词条 %d 个" % (ti, tf, tt))
out.append("")
out.append("注：并发额度与其它会话共享（若 zengyi 流水线同时在跑，会出现偶发并发拒绝，workflow 会自动重试补派）。")
out.append("")
out.append("| 卷 | 校对 | 修复 | 导读注释 | 问题数 | 修复数 | 词条数 |")
out.append("|----|------|------|----------|--------|--------|--------|")
out.extend(rows)
with open(os.path.join(".claude", "run-za-pipeline.md"), "w", encoding="utf-8") as fh:
    fh.write("\\n".join(out) + "\\n")
print("STATUS_WRITTEN vols=%d done3=%d" % (total, d3))`;

async function processVolume(n: number): Promise<VolumeStat> {
  const st: VolumeStat = { volume: n, checkIssues: 0, fixed: 0, rejected: 0, terms: 0, status: "完成", note: "" };
  try {
    phase("校对各卷译文");
    const c = await checkStage(n);
    st.checkIssues = c.issues;
    phase("按校对意见修复译文");
    const f = await fixStage(n);
    st.fixed = f.fixed;
    st.rejected = f.rejected;
    phase("生成导读与词语注释");
    const r = await readStage(n);
    st.terms = r.terms;
    await world.run("python3", ["-c", CLEANUP_PY, BOOK, String(n)]);
    if (c.skipped && f.skipped && r.skipped) {
      st.note = "此前已完成，跳过";
    } else if (f.fixed === 0 && f.skipped && !c.skipped) {
      st.note = "校对无问题，未修复";
    }
    log("✅ 卷" + n + " 完成：校对问题 " + st.checkIssues + "，修复 " + st.fixed + "，注释词条 " + st.terms);
  } catch (e) {
    st.status = "失败";
    st.note = String(e).slice(0, 280);
    log("❌ 卷" + n + " 失败：" + st.note);
  }
  report({ volume: n, checkIssues: st.checkIssues, fixed: st.fixed, terms: st.terms, status: st.status, note: st.note }, "za-progress");
  await world.run("python3", ["-c", STATUS_PY, BOOK]);
  return st;
}

const results: VolumeStat[] = await Promise.all(VOLS.map(processVolume));

phase("汇总状态并生成总报告");
await world.run("python3", ["-c", STATUS_PY, BOOK]);
const failed = results.filter(r => r.status === "失败");
const totalIssues = results.reduce((s, r) => s + Math.max(r.checkIssues, 0), 0);
const totalFixed = results.reduce((s, r) => s + Math.max(r.fixed, 0), 0);
const totalTerms = results.reduce((s, r) => s + Math.max(r.terms, 0), 0);
let md = "# 杂阿含经（za）1-50 卷三阶段流水线总报告\n\n";
md += "- 三阶段完成：" + (results.length - failed.length) + " / " + results.length + " 卷\n";
md += "- 校对问题合计：" + totalIssues + " 段；成立并修复：" + totalFixed + " 段；注释词条：" + totalTerms + " 个\n";
md += "- 并发经验：子代理并发上限 L=3（4 并发触发 user concurrency limit exceeded，与 chang 时期实测一致）\n";
md += "- 逐卷状态见 .claude/run-za-pipeline.md；报告/导读/注释在各卷 split/{N}.check.md / .fix.md / .guide.md / .notes.md\n";
if (failed.length > 0) {
  md += "\n## 失败卷（可重跑本工作流续跑，已完成的卷会自动跳过）\n\n";
  for (const f of failed) md += "- 卷" + f.volume + "：" + f.note + "\n";
}
await artifact.markdown("za-report", md, { title: "za 1-50 三阶段流水线总报告", primary: true });
log("全部结束：完成 " + (results.length - failed.length) + " 卷，失败 " + failed.length + " 卷");
return {
  volumes: results.length,
  completed: results.length - failed.length,
  failedVolumes: failed.map(f => f.volume),
  totalCheckIssues: totalIssues,
  totalFixed: totalFixed,
  totalTerms: totalTerms,
  concurrencyExperience: "L=3 稳定（4 并发触发 user concurrency limit exceeded）",
};
