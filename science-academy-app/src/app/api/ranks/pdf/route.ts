import { NextResponse, type NextRequest } from "next/server";
import { can, staffForApi } from "@/lib/auth";
import { logActivity } from "@/lib/activity";
import { boardName } from "@/lib/ids";
import { dateLabel } from "@/lib/format";
import { BANDS, getTest, loadRanking, rankScope, testCoversBatch } from "@/lib/academics";
import { allBatches } from "@/lib/batches";
import { drawFooters, drawHeader, drawTable, MARGIN, MUTED, NAVY, newDoc, pdfHeaders, toBuffer } from "@/lib/pdf";

/** Download the full ranking of one test as a PDF. */
export async function GET(req: NextRequest) {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "ranks.view")) return NextResponse.json({ error: "Not allowed" }, { status: 403 });
  const test = await getTest(req.nextUrl.searchParams.get("test") ?? "");
  if (!test) return NextResponse.json({ error: "Test not found" }, { status: 404 });
  const scope = rankScope(viewer);
  if (scope !== null) {
    const mine = (await allBatches(true)).filter((b) => scope.includes(b.id));
    if (!mine.some((b) => testCoversBatch(test, b))) return NextResponse.json({ error: "Test not found" }, { status: 404 });
  }
  const ranking = await loadRanking(test, viewer);
  const { summary } = ranking;
  const max = test.max_marks === null ? null : Number(test.max_marks);

  const doc = newDoc();
  let y = drawHeader(doc, {
    title: `Ranking · ${boardName(test.board)} Class ${test.class} · ${test.name}`,
    subtitle: [dateLabel(test.date), test.subject, test.tag, max !== null ? `Max marks ${max}` : null].filter(Boolean).join("  ·  "),
    right: ["Test ranking", `Printed ${dateLabel(new Date().toISOString().slice(0, 10))}`],
  });

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  doc.setTextColor(...NAVY);
  const summaryLine = [
    `Appeared: ${summary.appeared}`,
    `Absent: ${summary.absent}`,
    `Class average: ${summary.average !== null ? `${summary.average}%` : "-"}`,
    `Highest: ${summary.highest !== null ? `${summary.highest}%` : "-"}`,
  ].join("     ");
  doc.text(summaryLine, MARGIN, y);
  y += 5;
  doc.setTextColor(...MUTED);
  doc.text(`Score bands: ${BANDS.map((b) => `${b.replace("–", "-")}: ${summary.bands[b]}`).join("   ")}`, MARGIN, y);
  y += 4;
  if (ranking.limited) {
    y += 1;
    doc.text("Only students of the batches this login may see are listed. Ranks are class ranks.", MARGIN, y);
    y += 4;
  }
  y += 2;

  drawTable(
    doc,
    [
      { header: "Rank", width: 16, align: "center" },
      { header: "Student", width: 62 },
      { header: "ID", width: 32 },
      { header: "Batch", width: 34 },
      { header: "Score", width: 20, align: "right" },
      { header: "%", width: 18, align: "right" },
    ],
    ranking.rows.map((r) => [
      String(r.rank),
      r.student.name,
      r.student.code ?? "",
      r.batch,
      max !== null ? `${r.score} / ${max}` : String(r.score),
      r.pct !== null ? `${r.pct}%` : "",
    ]),
    y,
    { bold: ranking.rows.map((r, i) => (r.rank <= 3 ? i : -1)).filter((i) => i >= 0) },
  );
  drawFooters(doc);

  await logActivity(viewer, "export.ranks", { type: "test", id: test.id }, { test: test.name, rows: ranking.rows.length });
  const name = `Ranking ${boardName(test.board)} ${test.class} ${test.name} ${test.date}.pdf`;
  return new NextResponse(new Uint8Array(toBuffer(doc)), { headers: pdfHeaders(name) });
}
