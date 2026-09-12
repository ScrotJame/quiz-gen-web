"use client";

import React from "react";
import { LucideIcon } from "lucide-react";

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  badgeText?: string;
  accentColor: "indigo" | "emerald" | "amber" | "purple" | "sky";
  progressPercent?: number;
}

const colorVariants = {
  indigo: {
    bgLight: "bg-indigo-50 dark:bg-indigo-950/40",
    border: "border-indigo-100 dark:border-indigo-900/50",
    text: "text-indigo-600 dark:text-indigo-400",
    gradient: "from-indigo-600 to-blue-600",
    iconBg: "bg-gradient-to-tr from-indigo-500 to-indigo-600 text-white",
    progressBg: "bg-indigo-500",
    glow: "group-hover:shadow-indigo-500/10",
  },
  emerald: {
    bgLight: "bg-emerald-50 dark:bg-emerald-950/40",
    border: "border-emerald-100 dark:border-emerald-900/50",
    text: "text-emerald-600 dark:text-emerald-400",
    gradient: "from-emerald-600 to-teal-600",
    iconBg: "bg-gradient-to-tr from-emerald-500 to-teal-600 text-white",
    progressBg: "bg-emerald-500",
    glow: "group-hover:shadow-emerald-500/10",
  },
  amber: {
    bgLight: "bg-amber-50 dark:bg-amber-950/40",
    border: "border-amber-100 dark:border-amber-900/50",
    text: "text-amber-600 dark:text-amber-400",
    gradient: "from-amber-500 to-orange-600",
    iconBg: "bg-gradient-to-tr from-amber-500 to-orange-600 text-white",
    progressBg: "bg-amber-500",
    glow: "group-hover:shadow-amber-500/10",
  },
  purple: {
    bgLight: "bg-purple-50 dark:bg-purple-950/40",
    border: "border-purple-100 dark:border-purple-900/50",
    text: "text-purple-600 dark:text-purple-400",
    gradient: "from-purple-600 to-pink-600",
    iconBg: "bg-gradient-to-tr from-purple-500 to-pink-600 text-white",
    progressBg: "bg-purple-500",
    glow: "group-hover:shadow-purple-500/10",
  },
  sky: {
    bgLight: "bg-sky-50 dark:bg-sky-950/40",
    border: "border-sky-100 dark:border-sky-900/50",
    text: "text-sky-600 dark:text-sky-400",
    gradient: "from-sky-500 to-blue-600",
    iconBg: "bg-gradient-to-tr from-sky-500 to-blue-600 text-white",
    progressBg: "bg-sky-500",
    glow: "group-hover:shadow-sky-500/10",
  },
};

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  badgeText,
  accentColor,
  progressPercent,
}: StatCardProps) {
  const styles = colorVariants[accentColor];

  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border ${styles.border} bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${styles.glow} dark:bg-zinc-900`}
    >
      {/* Subtle background glow circle */}
      <div
        className={`absolute -right-6 -top-6 h-28 w-28 rounded-full opacity-15 blur-2xl transition-opacity duration-300 group-hover:opacity-30 ${styles.progressBg}`}
      />

      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            {title}
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-zinc-900 dark:text-white">
              {value}
            </span>
            {badgeText && (
              <span
                className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${styles.bgLight} ${styles.text}`}
              >
                {badgeText}
              </span>
            )}
          </div>
        </div>

        {/* Icon container */}
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl shadow-md transition-transform duration-300 group-hover:scale-110 ${styles.iconBg}`}
        >
          <Icon className="h-6 w-6" />
        </div>
      </div>

      {/* Progress Bar (if provided, e.g. for average score) */}
      {progressPercent !== undefined && (
        <div className="mt-4">
          <div className="flex justify-between text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">
            <span>Hiệu suất đạt</span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">
              {progressPercent}%
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${styles.progressBg}`}
              style={{ width: `${Math.min(Math.max(progressPercent, 0), 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Subtitle */}
      {subtitle && (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
          {subtitle}
        </p>
      )}
    </div>
  );
}
