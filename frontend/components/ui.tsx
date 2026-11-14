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
    primary: "bg-slate-900 text-white hover:bg-slate-800 border border-slate-900 shadow-sm active:scale-[0.98]",
    hero: "bg-indigo-600 text-white hover:bg-indigo-700 border border-indigo-600 shadow-sm hover:shadow active:scale-[0.98] font-semibold",
    secondary: "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 hover:border-slate-400 shadow-xs active:scale-[0.98]",
    ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
    danger: "bg-rose-600 text-white hover:bg-rose-700 border border-rose-600 shadow-sm active:scale-[0.98]",
  }[variant];
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold tracking-tight transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none",
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
    <section className={cx("rounded-2xl border border-slate-200/90 bg-white p-6 shadow-xs transition-all duration-150", className)}>
      {children}
    </section>
  );
}

type Tone = "neutral" | "ok" | "warn" | "bad" | "info" | "accent";
export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: React.ReactNode; title?: string }) {
  const t = {
    neutral: "bg-slate-100 text-slate-700 border-slate-200",
    ok: "bg-emerald-50 text-emerald-800 border-emerald-200",
    warn: "bg-amber-50 text-amber-900 border-amber-200",
    bad: "bg-rose-50 text-rose-800 border-rose-200",
    info: "bg-sky-50 text-sky-800 border-sky-200",
    accent: "bg-indigo-50 text-indigo-800 border-indigo-200",
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
        "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold tracking-tight whitespace-nowrap",
        t,
      )}
    >
      <span className={cx("h-2 w-2 rounded-full shrink-0", dot)} />
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
        small ? "h-4 w-4" : "h-6 w-6",
      )}
    />
  );
}

export function Loading({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 p-16 text-sm font-medium text-slate-500">
      <Spinner /> {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-2xl border border-rose-200 bg-rose-50/80 p-5 text-sm font-medium text-rose-800 flex items-center justify-between gap-4"
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
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-300 p-16 text-center bg-white/60">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 font-bold text-lg mb-1">
        ∅
      </div>
      <p className="font-bold text-base text-slate-900">{title}</p>
      {hint && <p className="max-w-md text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ConfidenceBar({ value, label }: { value: number; label?: string }) {
  const tone = value >= 0.75 ? "bg-emerald-500" : value >= 0.5 ? "bg-amber-500" : "bg-rose-500";
  const pct = Math.round(value * 100);
  return (
    <div className="inline-flex items-center gap-2.5" title="Yapay zekâ kalibre edilmiş güven tahmini">
      <div className="h-2 w-20 overflow-hidden rounded-full bg-slate-100 border border-slate-200">
        <div className={cx("h-full rounded-full transition-all duration-300", tone)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-bold tabular-nums text-slate-700">{label ?? `%${pct}`}</span>
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
        "m-auto rounded-3xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-900/40 backdrop:backdrop-blur-sm",
        wide ? "w-[min(960px,95vw)]" : "w-[min(600px,95vw)]",
      )}
    >
      <div className="flex items-center justify-between border-b border-slate-100 px-7 py-5">
        <h2 className="font-bold text-lg text-slate-900">{title}</h2>
        <button
          onClick={onClose}
          aria-label="Kapat"
          className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors cursor-pointer"
        >
          ✕
        </button>
      </div>
      <div className="max-h-[75vh] overflow-y-auto p-7">{children}</div>
    </dialog>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2 text-sm">
      <span className="font-semibold text-slate-800">{label}</span>
      {children}
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-800 shadow-xs outline-none transition-all placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20";

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
    <div role="tablist" className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 rounded-t-2xl shadow-xs overflow-x-auto">
      {items.map((it) => {
        const active = value === it.id;
        return (
          <button
            key={it.id}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(it.id)}
            className={cx(
              "-mb-px inline-flex items-center gap-2 border-b-2 px-4 py-3.5 text-sm font-semibold transition-all cursor-pointer whitespace-nowrap",
              active
                ? "border-indigo-600 text-indigo-700 font-bold"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800",
            )}
          >
            {it.label}
            {it.count !== undefined && (
              <span
                className={cx(
                  "rounded-full px-2 py-0.5 text-xs font-bold tabular-nums",
                  active ? "bg-indigo-100 text-indigo-800" : "bg-slate-100 text-slate-600",
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
      <p className="text-sm text-slate-600 leading-relaxed">{body}</p>
      <div className="mt-7 flex justify-end gap-3">
        <Button onClick={onClose}>Vazgeç</Button>
        <Button variant="primary" onClick={onConfirm} loading={busy}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
