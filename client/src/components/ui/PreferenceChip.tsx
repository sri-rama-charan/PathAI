// ==============================================================================
// File: client/src/components/ui/PreferenceChip.tsx
// Purpose: Interactive filter chip following Vercel Geist monochrome button scales.
//
// What this component does:
// 1. Renders a toggleable option with a clean vector icon.
// 2. Uses pure white (#FFFFFF) background with black text when selected.
// 3. Emits onToggle event to the parent form.
// ==============================================================================

import React from 'react';
import type { ResourcePreference } from '../../types/form';
import { LuCheck, LuVideo, LuFileText, LuGraduationCap, LuCode } from 'react-icons/lu';

interface PreferenceChipProps {
  label: ResourcePreference;
  selected: boolean;
  onToggle: (label: ResourcePreference) => void;
}

// Map each resource preference to a dedicated vector icon
const ICONS: Record<ResourcePreference, React.ReactElement> = {
  Videos: <LuVideo className="w-3.5 h-3.5" />,
  Documentation: <LuFileText className="w-3.5 h-3.5" />,
  Courses: <LuGraduationCap className="w-3.5 h-3.5" />,
  Projects: <LuCode className="w-3.5 h-3.5" />,
};

export const PreferenceChip: React.FC<PreferenceChipProps> = ({
  label,
  selected,
  onToggle,
}) => {
  return (
    <button
      type="button"
      onClick={() => onToggle(label)}
      aria-pressed={selected}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer border ${
        selected
          ? 'bg-[#FFFFFF] border-[#FFFFFF] text-[#000000] shadow-sm'
          : 'bg-[#000000] border-[#262626] text-[#888888] hover:border-[#404040] hover:text-[#EDEDED]'
      }`}
    >
      <span className={selected ? 'text-[#0070F3]' : 'text-[#666666]'}>
        {ICONS[label]}
      </span>
      <span>{label}</span>
      {selected && (
        <LuCheck className="w-3 h-3 text-[#000000] ml-0.5" />
      )}
    </button>
  );
};

export default PreferenceChip;
