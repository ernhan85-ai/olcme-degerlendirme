"use client";

import { useEffect, useRef } from "react";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "hero";
  loading?: boolean;
};

export function Button({ variant = "secondary", loading, className, children, disabled, ...rest }: BtnProps) {
  const styles = {
    primary: "bg-slate-900 text-white hover:bg-slate-800 border border-slate-900 shadow-2xs active:scale-[0.98]",
    hero: "bg-indigo-600 text-white hover:bg-indigo-700 border border-indigo-600 shadow-2xs hover:shadow-xs active:scale-[0.98] font-semibold",
    secondary: "bg-white text-slate-700 border border-slate-200/90 hover:bg-slate-50 hover:border-slate-300 shadow-2xs active:scale-[0.98]",
    ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
    danger: "bg-rose-600 text-white hover:bg-rose-700 border border-rose-600 shadow-2xs active:scale-[0.98]",
  }[variant];
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold tracking-tight transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none",
        styles,
        className,
      )}
    >
      {loading && <Spinner small />}
      {children}
    </button>
  );
}

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <section className={cx("rounded-xl border border-slate-200/80 bg-white shadow-2xs transition-all duration-150", className)}>
      {children}
    </section>
  );
}

type Tone = "neutral" | "ok" | "warn" | "bad" | "info" | "accent";
export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: React.ReactNode; title?: string }) {
  const t = {
    neutral: "bg-slate-100 text-slate-600 border-slate-200/80",
    ok: "bg-emerald-50 text-emerald-700 border-emerald-200/70",
    warn: "bg-amber-50 text-amber-800 border-amber-200/70",
    bad: "bg-rose-50 text-rose-700 border-rose-200/70",
    info: "bg-sky-50 text-sky-700 border-sky-200/70",
    accent: "bg-indigo-50 text-indigo-700 border-indigo-200/70",
  }[tone];
  const dot = {
    neutral: "bg-slate-400",
    ok: "bg-emerald-500",
    warn: "bg-amber-500",
    bad: "bg-rose-500",
    info: "bg-sky-500",
    accent: "bg-indigo-500",
  }[tone];
  return (
    <span
      title={title}
      className={cx(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-semibold tracking-tight whitespace-nowrap",
        t,
      )}
    >
      <span className={cx("h-1.5 w-1.5 rounded-full shrink-0", dot)} />
      {children}
    </span>
  );
}

export function MockBadge() {
  return (
    <Badge tone="warn" title="Gerçek yapay zekâ sağlayıcısı yapılandırılmadı; sonuçlar simülasyondur.">
      SİMÜLASYON
    </Badge>
  );
}

export function Spinner({ small }: { small?: boolean }) {
  return (
    <span
      aria-hidden
      className={cx(
        "inline-block animate-spin rounded-full border-2 border-current border-r-transparent",
        small ? "h-3.5 w-3.5" : "h-5 w-5",
      )}
    />
  );
}

export function Loading({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 p-12 text-xs font-medium text-slate-500">
      <Spinner small /> {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-rose-200 bg-rose-50/70 p-4 text-xs font-medium text-rose-800 flex items-start justify-between gap-4"
    >
      <span>{message}</span>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary">
          Tekrar dene
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-200 p-12 text-center bg-white/50">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-400 font-bold mb-1">
        ∅
      </div>
      <p className="font-semibold text-sm text-slate-800">{title}</p>
      {hint && <p className="max-w-sm text-xs text-slate-500">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ConfidenceBar({ value, label }: { value: number; label?: string }) {
  const tone = value >= 0.75 ? "bg-emerald-500" : value >= 0.5 ? "bg-amber-500" : "bg-rose-500";
  const pct = Math.round(value * 100);
  return (
    <div className="inline-flex items-center gap-2" title="Yapay zekâ kalibre edilmiş güven tahmini">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100 border border-slate-200/50">
        <div className={cx("h-full rounded-full transition-all duration-300", tone)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-semibold tabular-nums text-slate-600">{label ?? `%${pct}`}</span>
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className={cx(
        "m-auto rounded-2xl border border-slate-200 bg-white p-0 text-slate-900 shadow-xl backdrop:bg-slate-900/40 backdrop:backdrop-blur-xs",
        wide ? "w-[min(920px,95vw)]" : "w-[min(560px,95vw)]",
      )}
    >
      <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <h2 className="font-bold text-base text-slate-900">{title}</h2>
        <button
          onClick={onClose}
          aria-label="Kapat"
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors cursor-pointer"
        >
          ✕
        </button>
      </div>
      <div className="max-h-[75vh] overflow-y-auto p-6">{children}</div>
    </dialog>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="font-semibold text-slate-700">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 shadow-2xs outline-none transition-all placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15";

export function Tabs<T extends string>({
  value,
  onChange,
  items,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { id: T; label: string; count?: number }[];
}) {
  return (
    <div role="tablist" className="flex items-center gap-1 border-b border-slate-200 bg-white px-2 rounded-t-xl">
      {items.map((it) => {
        const active = value === it.id;
        return (
          <button
            key={it.id}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(it.id)}
            className={cx(
              "-mb-px inline-flex items-center gap-2 border-b-2 px-3.5 py-2.5 text-xs font-semibold transition-all cursor-pointer",
              active
                ? "border-indigo-600 text-indigo-700 font-bold"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700",
            )}
          >
            {it.label}
            {it.count !== undefined && (
              <span
                className={cx(
                  "rounded-full px-1.5 py-0.2 text-[10px] font-bold tabular-nums",
                  active ? "bg-indigo-100 text-indigo-800" : "bg-slate-100 text-slate-500",
                )}
              >
                {it.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function Confirm({
  open,
  title,
  body,
  confirmLabel,
  onConfirm,
  onClose,
  busy,
}: {
  open: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onClose: () => void;
  busy?: boolean;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-xs text-slate-600 leading-relaxed">{body}</p>
      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={onClose}>Vazgeç</Button>
        <Button variant="primary" onClick={onConfirm} loading={busy}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
