// ==============================================================================
// File: client/src/components/ui/FormField.tsx
// Purpose: Reusable form field wrapper adhering to Vercel Geist design guidelines.
//
// What this component does:
// 1. Renders clean, high-contrast labels (#A1A1A1).
// 2. Uses subtle asterisk and hints with balanced typography.
// 3. Displays crisp red error alerts when validation fails.
// ==============================================================================

import React from 'react';
import { LuCircleAlert } from 'react-icons/lu';

interface FormFieldProps {
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}

export const FormField: React.FC<FormFieldProps> = ({
  id,
  label,
  required = false,
  hint,
  error,
  children,
}) => {
  return (
    <div className="space-y-2 text-left">
      {/* Label and Hint */}
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="block text-xs font-medium text-[#A1A1A1] tracking-normal">
          {label} {required && <span className="text-[#666666] ml-0.5" title="Required">*</span>}
        </label>
        {hint && !error && (
          <span className="text-xs text-[#666666] font-normal">{hint}</span>
        )}
      </div>

      {/* Input element */}
      {children}

      {/* Error state */}
      {error && (
        <p className="text-xs text-[#EE0000] font-medium flex items-center gap-1.5 mt-1.5">
          <LuCircleAlert className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
};

export default FormField;
