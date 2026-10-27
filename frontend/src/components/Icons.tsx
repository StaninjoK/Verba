// Minimal inline icon set (stroke icons, 1.6px, 20px grid). Decorative unless a title is given.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Icon({ size = 18, children, ...rest }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const UploadIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 13V3.5M6 7l4-4 4 4" />
    <path d="M3.5 12.5v2A2.5 2.5 0 0 0 6 17h8a2.5 2.5 0 0 0 2.5-2.5v-2" />
  </Icon>
);
export const SearchIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="9" cy="9" r="5.5" />
    <path d="m13.2 13.2 3.3 3.3" />
  </Icon>
);
export const SunIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="10" r="3.4" />
    <path d="M10 2.5v1.6M10 15.9v1.6M2.5 10h1.6M15.9 10h1.6M4.7 4.7l1.1 1.1M14.2 14.2l1.1 1.1M4.7 15.3l1.1-1.1M14.2 5.8l1.1-1.1" />
  </Icon>
);
export const MoonIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M16.2 12.2A6.6 6.6 0 0 1 7.8 3.8a6.6 6.6 0 1 0 8.4 8.4Z" />
  </Icon>
);
export const MonitorIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="2.8" y="3.5" width="14.4" height="10" rx="1.8" />
    <path d="M7 16.5h6M10 13.5v3" />
  </Icon>
);
export const ArrowLeftIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M16 10H4M8.5 5.5 4 10l4.5 4.5" />
  </Icon>
);
export const ArrowRightIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 10h12M11.5 5.5 16 10l-4.5 4.5" />
  </Icon>
);
export const CopyIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="6.5" y="6.5" width="10" height="10" rx="2" />
    <path d="M13.5 6.5V5a1.5 1.5 0 0 0-1.5-1.5H5A1.5 1.5 0 0 0 3.5 5v7A1.5 1.5 0 0 0 5 13.5h1.5" />
  </Icon>
);
export const DownloadIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 3.5V13M6 9l4 4 4-4" />
    <path d="M3.5 16.5h13" />
  </Icon>
);
export const TrashIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3.5 5.5h13M8 5.5V4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1.5M5.2 5.5l.7 10.1A1.5 1.5 0 0 0 7.4 17h5.2a1.5 1.5 0 0 0 1.5-1.4l.7-10.1" />
  </Icon>
);
export const PencilIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m12.8 4.2 3 3L7.5 15.5l-3.7.7.7-3.7 8.3-8.3Z" />
  </Icon>
);
export const DotsIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="5" cy="10" r=".9" fill="currentColor" />
    <circle cx="10" cy="10" r=".9" fill="currentColor" />
    <circle cx="15" cy="10" r=".9" fill="currentColor" />
  </Icon>
);
export const ShieldIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 2.8 4 5v4.6c0 3.6 2.6 6.4 6 7.6 3.4-1.2 6-4 6-7.6V5l-6-2.2Z" />
    <path d="m7.4 10 1.8 1.8 3.4-3.6" />
  </Icon>
);
export const AlertIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 3.2 2.6 16h14.8L10 3.2Z" />
    <path d="M10 8.2v3.4M10 13.9v.1" />
  </Icon>
);
export const InfoIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="10" r="7" />
    <path d="M10 9v4.5M10 6.5v.1" />
  </Icon>
);
export const CheckIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m4.5 10.5 3.5 3.5 7.5-8" />
  </Icon>
);
export const XIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m5 5 10 10M15 5 5 15" />
  </Icon>
);
export const ChevronUpIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m5 12.5 5-5 5 5" />
  </Icon>
);
export const ChevronDownIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m5 7.5 5 5 5-5" />
  </Icon>
);
export const PlayIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6.5 4.5v11l9-5.5-9-5.5Z" fill="currentColor" stroke="none" />
  </Icon>
);
export const FileAudioIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M11.5 2.5H6A1.5 1.5 0 0 0 4.5 4v12A1.5 1.5 0 0 0 6 17.5h8a1.5 1.5 0 0 0 1.5-1.5V6.5l-4-4Z" />
    <path d="M11.5 2.5v4h4M8 10.5v3M10 9v6M12 11v2" />
  </Icon>
);
export const FileVideoIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="2.5" y="5" width="11" height="10" rx="2" />
    <path d="m13.5 9 4-2.5v7l-4-2.5" />
  </Icon>
);
export const GlobeIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="10" r="7" />
    <path d="M3 10h14M10 3c2 2.2 2.8 4.5 2.8 7s-.8 4.8-2.8 7c-2-2.2-2.8-4.5-2.8-7S8 5.2 10 3Z" />
  </Icon>
);
export const CpuIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="5" y="5" width="10" height="10" rx="1.8" />
    <path d="M8 2.5V5M12 2.5V5M8 15v2.5M12 15v2.5M2.5 8H5M2.5 12H5M15 8h2.5M15 12h2.5" />
  </Icon>
);
export const ClockIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="10" r="7" />
    <path d="M10 6v4l2.5 1.8" />
  </Icon>
);
export const RefreshIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M16 10a6 6 0 1 1-1.8-4.3M16 3.5v3.2h-3.2" />
  </Icon>
);
