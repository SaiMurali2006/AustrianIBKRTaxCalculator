// Stroke-based 16x16 SVG icons (Design.md §11): stroke-width 1.5, round caps, currentColor.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Base({ size = 16, children, ...props }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {children}
    </svg>
  );
}

export const IconSummary = (p: IconProps) => (
  <Base {...p}><path d="M2 13V7M6 13V3M10 13V9M14 13V5" /></Base>
);
export const IconAudit = (p: IconProps) => (
  <Base {...p}><path d="M3 2h7l3 3v9H3zM10 2v3h3M5 8h6M5 11h4" /></Base>
);
export const IconPerf = (p: IconProps) => (
  <Base {...p}><path d="M2.5 10l3-3 2.5 2.5L13 4M9.5 4H13v3.5" /></Base>
);
export const IconUpload = (p: IconProps) => (
  <Base {...p}><path d="M8 10V2M5 5l3-3 3 3M2 11v2a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2" /></Base>
);
export const IconPot = (p: IconProps) => (
  <Base {...p}><path d="M2.5 6.5h11M4 6.5l1 7a1 1 0 0 0 1 .9h4a1 1 0 0 0 1-.9l1-7M8 8.5v3M6.5 10h3" /></Base>
);
export const IconClose = (p: IconProps) => (
  <Base {...p}><path d="M4 4l8 8M12 4l-8 8" /></Base>
);
export const IconChevron = (p: IconProps) => (
  <Base {...p}><path d="M6 4l4 4-4 4" /></Base>
);
export const IconDownload = (p: IconProps) => (
  <Base {...p}><path d="M8 2v8M5 7l3 3 3-3M2 13h12" /></Base>
);
export const IconWarn = (p: IconProps) => (
  <Base {...p}><path d="M8 2L1 14h14L8 2zM8 6v4M8 12h.01" /></Base>
);
export const IconInfo = (p: IconProps) => (
  <Base {...p}><circle cx="8" cy="8" r="6" /><path d="M8 7v4M8 5h.01" /></Base>
);
export const IconShield = (p: IconProps) => (
  <Base {...p}><path d="M8 2l5 2v4c0 3-2 5-5 6-3-1-5-3-5-6V4l5-2zM6 8l1.5 1.5L10 7" /></Base>
);
export const IconGear = ({ size = 16, ...props }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" {...props}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);
