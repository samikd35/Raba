'use client';

import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cofounderAPI } from '@/lib/api/cofounderService';
import { AFRICAN_COUNTRIES } from '@/lib/constants/countries';

export interface DirectoryFilters {
  languages: string[]; // language UUIDs
  preferred_commitment: string;
  preferred_venture_stage: string[];
  country: string;
}

export const defaultDirectoryFilters: DirectoryFilters = {
  languages: [],
  preferred_commitment: '',
  preferred_venture_stage: [],
  country: '',
};

interface LanguageOption {
  id: string;
  name: string;
}

interface FilterOptions {
  languages: LanguageOption[];
  commitments: string[];
  ventureStages: string[];
  countries: string[];
}

interface CofounderFilterProps {
  filters: DirectoryFilters;
  onChange: (nextFilters: DirectoryFilters) => void;
  onClear: () => void;
  className?: string;
  showLanguages?: boolean;
  showCommitment?: boolean;
  showVentureStage?: boolean;
  showCountry?: boolean;
}

const defaultOptions: FilterOptions = {
  languages: [],
  commitments: [],
  ventureStages: [],
  countries: [...AFRICAN_COUNTRIES],
};

const fallbackLanguages: LanguageOption[] = [
  { id: 'english', name: 'English' },
  { id: 'french', name: 'French' },
  { id: 'spanish', name: 'Spanish' },
];

const fallbackCommitments = ['Full-time', 'Part-time'];
const fallbackVentureStages = ['have ideas but open to explore', 'devoted to a venture'];

const CofounderFilter: React.FC<CofounderFilterProps> = ({
  filters,
  onChange,
  onClear,
  className = '',
  showLanguages = true,
  showCommitment = true,
  showVentureStage = true,
  showCountry = true,
}) => {
  const [options, setOptions] = useState<FilterOptions>(defaultOptions);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;

    const fetchOptions = async () => {
      setLoading(true);
      try {
        const [languagesRes, commitmentsRes, ventureStagesRes] = await Promise.all([
          cofounderAPI.enums.listLanguages({ pageSize: 500 }),
          cofounderAPI.enums.listCommitment({ pageSize: 100 }),
          cofounderAPI.enums.listVentureStages({ pageSize: 100 }),
        ]);

        if (!mounted) return;

        setOptions({
          languages: languagesRes.data.map((item) => ({ id: item.id, name: item.name })),
          commitments: commitmentsRes.data.map((item) => item.name),
          ventureStages: ventureStagesRes.data.map((item) => item.name),
          countries: [...AFRICAN_COUNTRIES],
        });
      } catch (error) {
        console.error('[CofounderFilter] Failed to load enums:', error);
        if (!mounted) return;
        setOptions({
          languages: fallbackLanguages,
          commitments: fallbackCommitments,
          ventureStages: fallbackVentureStages,
          countries: [...AFRICAN_COUNTRIES],
        });
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchOptions();

    return () => {
      mounted = false;
    };
  }, []);

  const updateFilters = (updates: Partial<DirectoryFilters>) => {
    onChange({
      ...filters,
      ...updates,
    });
  };

  const handleSingleSelect = (field: keyof DirectoryFilters, value?: string) => {
    const normalizedValue = value ?? '';
    if (field === 'preferred_commitment' || field === 'country') {
      updateFilters({ [field]: normalizedValue } as Partial<DirectoryFilters>);
      return;
    }

    const nextValue = normalizedValue ? [normalizedValue] : [];
    updateFilters({ [field]: nextValue } as Partial<DirectoryFilters>);
  };

  const hasActiveFilters =
    filters.languages.length > 0 ||
    Boolean(filters.preferred_commitment) ||
    filters.preferred_venture_stage.length > 0 ||
    Boolean(filters.country);

  const selectDisabled = loading && options.languages.length === 0;

  const renderSelect = (
    shouldShow: boolean,
    label: string,
    value: string | undefined,
    onValueChange: (val: string) => void,
    items: Array<{ value: string; label: string }>
  ) => {
    if (!shouldShow) return null;
    return (
      <Select value={value} onValueChange={onValueChange} disabled={selectDisabled}>
        <SelectTrigger className="min-w-[140px] w-full sm:w-[150px] lg:w-[170px] flex-1 sm:flex-none">
          <SelectValue placeholder={label} />
        </SelectTrigger>
        <SelectContent>
          {items.map((item) => (
            <SelectItem key={item.value} value={item.value}>
              {item.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  };

  return (
    <div className={`flex flex-wrap gap-3 items-center ${className}`}>
      {renderSelect(
        showLanguages,
        'Languages',
        filters.languages[0],
        (val) => handleSingleSelect('languages', val),
        options.languages.map((lang) => ({ value: lang.id, label: lang.name }))
      )}

      {renderSelect(
        showCommitment,
        'Commitment',
        filters.preferred_commitment || undefined,
        (val) => handleSingleSelect('preferred_commitment', val),
        options.commitments.map((commitment) => ({ value: commitment, label: commitment }))
      )}

      {renderSelect(
        showVentureStage,
        'Venture Stage',
        filters.preferred_venture_stage[0],
        (val) => handleSingleSelect('preferred_venture_stage', val),
        options.ventureStages.map((stage) => ({ value: stage, label: stage }))
      )}

      {renderSelect(
        showCountry,
        'Country',
        filters.country || undefined,
        (val) => handleSingleSelect('country', val),
        options.countries.map((country) => ({ value: country, label: country }))
      )}

      {hasActiveFilters && (
        <button
          type="button"
          onClick={onClear}
          className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 flex items-center gap-1"
        >
          <X className="w-4 h-4" />
          Clear
        </button>
      )}
    </div>
  );
};

export default CofounderFilter;
