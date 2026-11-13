"use client";

import { useState } from "react";
import { fileUrl } from "@/lib/api";
import type { SubmissionFile } from "@/lib/types";
import { cx } from "./ui";

export interface Box { id: string; page: number | null; bbox: number[] | null; tone: "step" | "invalid" | "answer" | "evidence"; label?: string }

const toneCls: Record<Box["tone"], string> = {
  step: "stroke-[var(--color-info)] fill-[var(--color-info)]/5",
  invalid: "stroke-[var(--color-bad)] fill-[var(--color-bad)]/10",
  answer: "stroke-[var(--color-accent)] fill-[var(--color-accent)]/5",
  evidence: "stroke-[var(--color-warn)] fill-[var(--color-warn)]/20",
};

/** Shows the scanned pages with normalized [x0,y0,x1,y1] bounding boxes overlaid.
 *  Images: one file = one page. PDFs are shown natively without overlays (v1 limitation). */
export function DocumentViewer({ files, boxes, highlight, initialPage }: {
  files: SubmissionFile[]; boxes: Box[]; highlight: string | null; initialPage?: number | null;
}) {
  const [page, setPage] = useState(Math.max(1, Math.min(initialPage ?? 1, Math.max(files.length, 1))));
  if (!files.length) {
    return (
      <div className="flex h-full min-h-80 items-center justify-center rounded-xl border border-dashed border-line p-8 text-center text-sm text-muted">
        Bu kayıt için taranmış görüntü yok (geliştirme ortamı transkripsiyon dosyası). Bölge işaretleri yalnızca gerçek taramalarda gösterilir.
      </div>
    );
  }
  const f = files[page - 1];
  const pageBoxes = boxes.filter((b) => b.bbox && (b.page ?? 1) === page);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-sm">
        <span className="truncate text-muted">{f.original_name}</span>
        {files.length > 1 && (
          <div className="flex items-center gap-2">
            <button className="rounded px-2 hover:bg-line/50 disabled:opacity-30" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Önceki sayfa">‹</button>
            <span className="tabular-nums">{page} / {files.length}</span>
            <button className="rounded px-2 hover:bg-line/50 disabled:opacity-30" disabled={page >= files.length} onClick={() => setPage(page + 1)} aria-label="Sonraki sayfa">›</button>
          </div>
        )}
      </div>
      {f.mime_type === "application/pdf" ? (
        <iframe title="Öğrenci kitapçığı" src={fileUrl(f.id)} className="h-[70vh] w-full rounded-xl border border-line bg-white" />
      ) : (
        <div className="relative overflow-hidden rounded-xl border border-line bg-white">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={fileUrl(f.id)} alt={`Öğrenci kâğıdı, sayfa ${page}`} className="block w-full" />
          <svg viewBox="0 0 1 1" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
            {pageBoxes.map((b) => {
              const [x0, y0, x1, y1] = b.bbox as number[];
              const on = highlight === b.id;
              return (
                <rect key={b.id} x={x0} y={y0} width={x1 - x0} height={y1 - y0} vectorEffect="non-scaling-stroke"
                  className={cx(toneCls[b.tone], on ? "stroke-[3px]" : "stroke-[1.5px]", !on && highlight ? "opacity-30" : "")} />
              );
            })}
          </svg>
        </div>
      )}
      {f.mime_type === "application/pdf" && <p className="text-xs text-muted">PDF görünümünde bölge işaretleri gösterilmez; sayfaları görüntü olarak yüklemek işaretlemeyi etkinleştirir.</p>}
    </div>
  );
}
