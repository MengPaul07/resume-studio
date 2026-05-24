import { ChevronDown, ChevronUp, RotateCcw } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';
import {
  DEFAULT_GUIDANCE,
  clamp,
  type BulletStyle,
  type BuilderSectionDraft,
  type ColumnMode,
  type DateStyle,
  type HeaderLayout,
  type ListLayoutMode,
  type PageCountMode,
  type PhotoPreset,
  type PhotoShape,
  type RenderGuidanceSettings,
  type SectionHeadingCase,
  type SectionHeadingStyle,
} from './types';

interface EditorPanelProps {
  guidance: RenderGuidanceSettings;
  onGuidanceChange: (next: RenderGuidanceSettings) => void;
  sections?: BuilderSectionDraft[];
  onSectionsChange?: (next: BuilderSectionDraft[]) => void;
  contentOverflows?: boolean;
}

interface SelectorProps<T extends string> {
  label: string;
  value: T;
  onChange: (next: T) => void;
  options: Array<{ value: T; text: string }>;
}

interface SliderProps {
  label: string;
  min: number;
  max: number;
  value: number;
  suffix?: string;
  step?: number;
  onChange: (next: number) => void;
}

type ControlGroup = 'page' | 'typography' | 'layout' | 'sections';

function SelectorButtons<T extends string>({ label, value, onChange, options }: SelectorProps<T>) {
  return (
    <div>
      <h4 className="mb-2 font-mono text-[11px] font-bold uppercase tracking-wider text-gray-600 dark:text-[var(--brand-ink-muted)]">{label}</h4>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`border px-3 py-1.5 font-sans text-xs font-medium transition-all ${
              value === option.value
                ? 'border-[var(--brand-signal)] bg-white dark:bg-[var(--brand-surface)] text-[var(--brand-signal)] shadow-sm'
                : 'border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] text-gray-700 dark:text-[var(--brand-ink)] hover:bg-gray-50 dark:hover:bg-[var(--brand-surface-soft)]'
            }`}
          >
            {option.text}
          </button>
        ))}
      </div>
    </div>
  );
}

function NumberSlider({ label, min, max, value, suffix = '', step, onChange }: SliderProps) {
  const safeValue = Number.isFinite(value) ? value : min;
  const formatValue = Number.isInteger(safeValue) ? String(safeValue) : safeValue.toFixed(1).replace(/\.0$/, '');
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={safeValue}
        onChange={(event) => onChange(Number.parseFloat(event.target.value))}
        className="h-1 flex-1 cursor-pointer appearance-none bg-gray-200 dark:bg-[var(--brand-surface-soft)]
                   [&::-webkit-slider-thumb]:h-3
                   [&::-webkit-slider-thumb]:w-3
                   [&::-webkit-slider-thumb]:appearance-none
                   [&::-webkit-slider-thumb]:bg-[var(--brand-signal)]
                   [&::-webkit-slider-thumb]:border-none
                   [&::-moz-range-thumb]:h-3
                   [&::-moz-range-thumb]:w-3
                   [&::-moz-range-thumb]:bg-[var(--brand-signal)]
                   [&::-moz-range-thumb]:border-none"
      />
      <span className="w-14 text-right font-mono text-[11px] text-gray-800 dark:text-[var(--brand-ink)]">
        {formatValue}
        {suffix}
      </span>
    </div>
  );
}

export function EditorPanel({ guidance, onGuidanceChange, sections = [], onSectionsChange, contentOverflows }: EditorPanelProps) {
  const { t } = useTranslation();
  const [controlsExpanded, setControlsExpanded] = useState(true);
  const [activeGroup, setActiveGroup] = useState<ControlGroup>('page');
  const photoInputRef = useRef<HTMLInputElement | null>(null);

  const updateGuidance = <K extends keyof RenderGuidanceSettings>(key: K, value: RenderGuidanceSettings[K]) => {
    onGuidanceChange({ ...guidance, [key]: value });
  };

  const updateMargin = (key: keyof RenderGuidanceSettings['margins'], value: number) => {
    onGuidanceChange({
      ...guidance,
      margins: {
        ...guidance.margins,
        [key]: value,
      },
    });
  };

  const handlePhotoFile = (file: File | null) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      window.alert('Please choose an image file.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = typeof reader.result === 'string' ? reader.result : '';
      if (!dataUrl) return;
      onGuidanceChange({
        ...guidance,
        showPhoto: true,
        photoUrl: dataUrl,
      });
    };
    reader.readAsDataURL(file);
  };

  const updatePhotoPreset = (preset: PhotoPreset) => {
    if (preset === 'one-inch') {
      onGuidanceChange({ ...guidance, photoPreset: preset, photoWidthMm: 25, photoHeightMm: 35, photoShape: 'rounded' });
      return;
    }
    if (preset === 'two-inch') {
      onGuidanceChange({ ...guidance, photoPreset: preset, photoWidthMm: 35, photoHeightMm: 49, photoShape: 'rounded' });
      return;
    }
    onGuidanceChange({ ...guidance, photoPreset: preset, photoWidthMm: 0, photoHeightMm: 0 });
  };

  const moveSection = (index: number, dir: -1 | 1) => {
    if (!onSectionsChange || !sections.length) return;
    const nextIndex = index + dir;
    if (nextIndex < 0 || nextIndex >= sections.length) return;
    const copied = [...sections];
    const [item] = copied.splice(index, 1);
    copied.splice(nextIndex, 0, item);
    onSectionsChange(copied);
  };

  const toggleSection = (index: number) => {
    if (!onSectionsChange || !sections.length) return;
    const copied = [...sections];
    copied[index] = { ...copied[index], visible: !copied[index].visible };
    onSectionsChange(copied);
  };

  const toggleColumn = (index: number) => {
    if (!onSectionsChange || !sections.length) return;
    const copied = [...sections];
    copied[index] = { ...copied[index], column: copied[index].column === 'left' ? 'right' : 'left' };
    onSectionsChange(copied);
  };

  const cyclePage = (index: number) => {
    if (!onSectionsChange || !sections.length) return;
    const copied = [...sections];
    const current = copied[index].page ?? 1;
    copied[index] = { ...copied[index], page: current >= 3 ? 1 : current + 1 };
    onSectionsChange(copied);
  };

  const groupTabs = useMemo(
    () =>
      [
        { key: 'page' as ControlGroup, text: t('editorPanel.page') },
        { key: 'typography' as ControlGroup, text: t('editorPanel.typography') },
        { key: 'layout' as ControlGroup, text: t('editorPanel.layout') },
        { key: 'sections' as ControlGroup, text: t('editorPanel.sections') },
      ],
    [t],
  );

  const fontOptions = [
    { value: 'serif' as const, text: t('editorPanel.serif') },
    { value: 'sans-serif' as const, text: t('editorPanel.sans') },
    { value: 'mono' as const, text: t('editorPanel.mono') },
  ];

  const bodyFontOptions = [
    { value: 'sans-serif' as const, text: t('editorPanel.sans') },
    { value: 'serif' as const, text: t('editorPanel.serif') },
    { value: 'mono' as const, text: t('editorPanel.mono') },
  ];

  const pageCountOptions = [
    { value: 'single-page' as const, text: t('editorPanel.singlePage') },
    { value: 'double-page' as const, text: t('editorPanel.twoPages') },
  ];

  const pageCountOverflowOptions = [
    { value: 'single-page' as const, text: t('editorPanel.singlePageUnavailable') },
    { value: 'double-page' as const, text: t('editorPanel.twoPages') },
  ];

  const columnModeOptions = [
    { value: 'single' as const, text: t('editorPanel.singleColumn') },
    { value: 'double' as const, text: t('editorPanel.doubleColumn') },
  ];

  const headingStyleOptions = [
    { value: 'underline' as const, text: t('editorPanel.underline') },
    { value: 'bar' as const, text: t('editorPanel.leftBar') },
    { value: 'boxed' as const, text: t('editorPanel.boxed') },
  ];

  const headingCaseOptions = [
    { value: 'uppercase' as const, text: t('editorPanel.upper') },
    { value: 'title' as const, text: t('editorPanel.title') },
  ];

  const dateStyleOptions = [
    { value: 'muted' as const, text: t('editorPanel.belowTitle') },
    { value: 'inline' as const, text: t('editorPanel.inlineRight') },
    { value: 'bottom-inline' as const, text: t('editorPanel.bottomInline') },
  ];

  const bulletStyleOptions = [
    { value: 'disc' as const, text: t('editorPanel.disc') },
    { value: 'square' as const, text: t('editorPanel.square') },
    { value: 'dash' as const, text: t('editorPanel.dash') },
  ];

  const layoutOptions = [
    { value: 'vertical' as const, text: t('editorPanel.vertical') },
    { value: 'horizontal' as const, text: t('editorPanel.horizontal') },
  ];

  return (
    <div className="space-y-5">
      <div className="border-b border-[var(--brand-line)] pb-3">
        <div className="mb-2 flex items-center gap-2">
          <div className="h-3 w-3 bg-[var(--brand-signal)]" />
          <h3 className="font-mono text-xs font-bold uppercase tracking-[0.14em] text-[var(--brand-ink)] dark:text-zinc-200">{t('editorPanel.layoutControls')}</h3>
        </div>
        <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--brand-signal)]">
          {t('editorPanel.groupedConfig')}
        </p>
      </div>

      <div className="border border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] shadow-[4px_4px_0px_0px_rgba(0,0,0,0.1)]">
        <button
          type="button"
          onClick={() => setControlsExpanded((prev) => !prev)}
          className="flex w-full items-center justify-between p-3 transition-colors hover:bg-gray-50 dark:hover:bg-[var(--brand-surface-soft)]"
        >
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 bg-[var(--brand-signal)]" />
            <span className="font-mono text-xs font-bold uppercase tracking-wider text-[var(--brand-ink)] dark:text-zinc-200">{t('editorPanel.formattingControls')}</span>
          </div>
          {controlsExpanded ? <ChevronUp className="size-4 text-gray-500 dark:text-[var(--brand-ink-muted)]" /> : <ChevronDown className="size-4 text-gray-500 dark:text-[var(--brand-ink-muted)]" />}
        </button>

        {controlsExpanded ? (
          <div className="space-y-4 border-t border-[var(--brand-line)] p-4">
            {/* Compact level — prominent 5-degree selector */}
            <div>
              <h4 className="mb-2 font-mono text-[11px] font-bold uppercase tracking-wider text-[var(--brand-signal)]">{t('editorPanel.compactLevel')}</h4>
              <div className="grid grid-cols-5 gap-1">
                {([0, 1, 2, 3, 4] as const).map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => updateGuidance('compactLevel', level)}
                    className={`border px-2 py-1.5 font-sans text-xs font-medium transition-all ${
                      guidance.compactLevel === level
                        ? 'border-[var(--brand-signal)] bg-white dark:bg-[var(--brand-surface)] text-[var(--brand-signal)] shadow-sm'
                        : 'border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] text-gray-700 dark:text-[var(--brand-ink)] hover:bg-gray-50 dark:hover:bg-[var(--brand-surface-soft)]'
                    }`}
                  >
                    {t(`editorPanel.compactL${level}`)}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {groupTabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveGroup(tab.key)}
                  className={`border px-3 py-1.5 font-sans text-xs font-medium ${
                    activeGroup === tab.key
                      ? 'border-[var(--brand-signal)] bg-white dark:bg-[var(--brand-surface)] text-[var(--brand-signal)] shadow-sm'
                      : 'border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] text-gray-700 dark:text-[var(--brand-ink)]'
                  }`}
                >
                  {tab.text}
                </button>
              ))}
            </div>

            <div className="border border-[var(--brand-line)] p-3">
              {activeGroup === 'page' ? (
                <div className="space-y-3">
                  <h4 className="font-mono text-[11px] font-bold uppercase tracking-wider text-[var(--brand-signal)]">{t('editorPanel.page')}</h4>
                  <div className="border border-[var(--brand-line)] bg-[var(--brand-paper)] px-2 py-1 font-sans text-xs font-medium">
                    {t('editorPanel.pageFormat')}
                  </div>
                  {contentOverflows && guidance.pageCountMode === 'single-page' ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 border border-amber-400 dark:border-amber-500/50 bg-amber-50 dark:bg-amber-900/20 p-2 font-sans text-xs">
                        <span>⚠</span>
                        <span>{t('editorPanel.contentOverflow')}</span>
                      </div>
                      <SelectorButtons<PageCountMode>
                        label={t('editorPanel.pageCount')}
                        value="double-page"
                        onChange={(value) => {
                          if (contentOverflows && value === 'single-page') return;
                          updateGuidance('pageCountMode', value);
                        }}
                        options={pageCountOverflowOptions}
                      />
                    </div>
                  ) : (
                    <SelectorButtons<PageCountMode>
                      label={t('editorPanel.pageCount')}
                      value={guidance.pageCountMode}
                      onChange={(value) => updateGuidance('pageCountMode', value)}
                      options={contentOverflows
                        ? [{ value: 'single-page' as const, text: t('editorPanel.singlePageOverflow') }, { value: 'double-page' as const, text: t('editorPanel.twoPages') }]
                        : pageCountOptions}
                    />
                  )}
                  <NumberSlider label={t('editorPanel.sectionGap')} min={10} max={30} value={guidance.sectionGapPx} suffix="px" onChange={(value) => updateGuidance('sectionGapPx', clamp(value, 10, 30))} />
                  <NumberSlider label={t('editorPanel.itemGap')} min={6} max={18} value={guidance.itemGapPx} suffix="px" onChange={(value) => updateGuidance('itemGapPx', clamp(value, 6, 18))} />
                  <NumberSlider label={t('editorPanel.headingContentGap')} min={2} max={14} value={guidance.headingMarginBottomPx} suffix="px" onChange={(value) => updateGuidance('headingMarginBottomPx', clamp(value, 2, 14))} />
                  <h4 className="font-mono text-[11px] font-bold uppercase tracking-wider text-gray-600 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.margins')}</h4>
                  <NumberSlider label={t('editorPanel.top')} min={6} max={18} value={guidance.margins.top} onChange={(value) => updateMargin('top', value)} />
                  <NumberSlider label={t('editorPanel.bottom')} min={6} max={18} value={guidance.margins.bottom} onChange={(value) => updateMargin('bottom', value)} />
                  <NumberSlider label={t('editorPanel.left')} min={6} max={18} value={guidance.margins.left} onChange={(value) => updateMargin('left', value)} />
                  <NumberSlider label={t('editorPanel.right')} min={6} max={18} value={guidance.margins.right} onChange={(value) => updateMargin('right', value)} />
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.headerBgColor')}</span>
                    <input type="color" value={guidance.headerBgColor} onChange={(e) => updateGuidance('headerBgColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.headerBgColor}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.headerTextColor')}</span>
                    <input type="color" value={guidance.headerTextColor} onChange={(e) => updateGuidance('headerTextColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.headerTextColor}</span>
                  </div>
                  <label className="mt-2 flex cursor-pointer items-center gap-3">
                    <button
                      type="button"
                      onClick={() => updateGuidance('showPhoto', !guidance.showPhoto)}
                      className={`relative h-5 w-10 border-2 transition-all ${
                        guidance.showPhoto ? 'border-[var(--brand-signal)] bg-[var(--brand-signal)]' : 'border-gray-400 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)]'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 h-3.5 w-3.5 border bg-white dark:bg-zinc-200 transition-all ${
                          guidance.showPhoto ? 'left-5 border-[var(--brand-signal)]' : 'left-0.5 border-gray-400 dark:border-[var(--brand-line)]'
                        }`}
                      />
                    </button>
                    <span className="font-mono text-xs uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">{t('editorPanel.showPhoto')}</span>
                  </label>
                  {guidance.showPhoto ? (
                    <div className="space-y-2 border border-[var(--brand-line)] p-3">
                      <SelectorButtons<PhotoPreset>
                        label="Photo Size"
                        value={guidance.photoPreset || 'one-inch'}
                        onChange={updatePhotoPreset}
                        options={[
                          { value: 'one-inch' as const, text: '1 inch 25x35mm' },
                          { value: 'two-inch' as const, text: '2 inch 35x49mm' },
                          { value: 'custom-square' as const, text: 'Custom square' },
                        ]}
                      />
                      <div className="flex items-center gap-3">
                        <div
                          className="shrink-0 border border-[var(--brand-line)] bg-[var(--brand-surface-soft)] bg-cover bg-center"
                          style={{
                            width: guidance.photoPreset === 'two-inch' ? 40 : guidance.photoPreset === 'one-inch' ? 32 : 56,
                            height: guidance.photoPreset === 'two-inch' ? 56 : guidance.photoPreset === 'one-inch' ? 45 : 56,
                            borderRadius: guidance.photoShape === 'circle' ? 999 : guidance.photoShape === 'rounded' ? 12 : 0,
                            backgroundImage: guidance.photoUrl ? `url(${guidance.photoUrl})` : undefined,
                          }}
                        >
                          {!guidance.photoUrl ? (
                            <div className="flex h-full w-full items-center justify-center font-mono text-[10px] uppercase text-gray-400">
                              Photo
                            </div>
                          ) : null}
                        </div>
                        <div className="min-w-0 flex-1 space-y-2">
                          <input
                            ref={photoInputRef}
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={(event) => {
                              handlePhotoFile(event.target.files?.[0] || null);
                              event.currentTarget.value = '';
                            }}
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => photoInputRef.current?.click()}
                              className="rounded border border-[var(--brand-line)] px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wide text-gray-700 hover:border-[var(--brand-signal)] hover:text-[var(--brand-signal)] dark:text-[var(--brand-ink)]"
                            >
                              Import Image
                            </button>
                            {guidance.photoUrl ? (
                              <button
                                type="button"
                                onClick={() => updateGuidance('photoUrl', '')}
                                className="rounded border border-[var(--brand-line)] px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wide text-gray-500 hover:border-red-300 hover:text-red-500"
                              >
                                Clear
                              </button>
                            ) : null}
                          </div>
                          <p className="font-sans text-[11px] leading-snug text-gray-400 dark:text-[var(--brand-ink-muted)]">
                            Imported images are embedded into this template as a data URL.
                          </p>
                        </div>
                      </div>
                      <input
                        type="text"
                        value={guidance.photoUrl}
                        onChange={(e) => updateGuidance('photoUrl', e.target.value)}
                        placeholder="Image URL or imported data URL"
                        className="w-full border border-[var(--brand-line)] px-2 py-1.5 font-mono text-[11px] outline-none focus:border-[var(--brand-signal)]"
                      />
                      {guidance.photoPreset === 'custom-square' ? (
                        <NumberSlider label={t('editorPanel.photoSize')} min={48} max={96} value={guidance.photoSize} suffix="px" onChange={(value) => updateGuidance('photoSize', clamp(value, 48, 96))} />
                      ) : (
                        <div className="rounded border border-[var(--brand-line)] bg-[var(--brand-surface-soft)] px-2 py-1.5 font-mono text-[10px] uppercase tracking-wide text-gray-500 dark:text-[var(--brand-ink-muted)]">
                          Print size: {guidance.photoWidthMm || 25} x {guidance.photoHeightMm || 35} mm
                        </div>
                      )}
                      <SelectorButtons<PhotoShape>
                        label={t('editorPanel.photoShape')}
                        value={guidance.photoShape}
                        onChange={(value) => updateGuidance('photoShape', value)}
                        options={[
                          { value: 'rounded' as const, text: t('editorPanel.rounded') },
                          { value: 'square' as const, text: t('editorPanel.square') },
                          { value: 'circle' as const, text: t('editorPanel.circle') },
                        ]}
                      />
                      <SelectorButtons<'left' | 'right'>
                        label={t('editorPanel.photoPosition')}
                        value={guidance.photoPosition}
                        onChange={(value) => updateGuidance('photoPosition', value)}
                        options={[
                          { value: 'left' as const, text: t('editorPanel.left') },
                          { value: 'right' as const, text: t('editorPanel.right') },
                        ]}
                      />
                    </div>
                  ) : null}
                </div>
              ) : null}

              {activeGroup === 'typography' ? (
                <div className="space-y-3">
                  <h4 className="font-mono text-[11px] font-bold uppercase tracking-wider text-[var(--brand-signal)]">{t('editorPanel.typography')}</h4>
                  <SelectorButtons<'serif' | 'sans-serif' | 'mono'>
                    label={t('editorPanel.headerFont')}
                    value={guidance.headerFont}
                    onChange={(value) => updateGuidance('headerFont', value)}
                    options={fontOptions}
                  />
                  <SelectorButtons<'serif' | 'sans-serif' | 'mono'>
                    label={t('editorPanel.bodyFont')}
                    value={guidance.bodyFont}
                    onChange={(value) => updateGuidance('bodyFont', value)}
                    options={bodyFontOptions}
                  />
                  <SelectorButtons<HeaderLayout>
                    label={t('editorPanel.headerLayout')}
                    value={guidance.headerLayout}
                    onChange={(value) => updateGuidance('headerLayout', value)}
                    options={[
                      { value: 'left' as const, text: t('editorPanel.left') },
                      { value: 'center' as const, text: t('editorPanel.center') },
                      { value: 'split' as const, text: t('editorPanel.split') },
                    ]}
                  />
                  <NumberSlider label={t('editorPanel.nameSize')} min={26} max={44} value={guidance.nameFontSizePx} suffix="px" onChange={(value) => updateGuidance('nameFontSizePx', clamp(value, 26, 44))} />
                  <NumberSlider label={t('editorPanel.nameWeight')} min={300} max={900} step={100} value={guidance.nameFontWeight} suffix="" onChange={(value) => updateGuidance('nameFontWeight', clamp(value, 300, 900))} />
                  <NumberSlider label={t('editorPanel.roleSize')} min={12} max={20} value={guidance.roleFontSizePx} suffix="px" onChange={(value) => updateGuidance('roleFontSizePx', clamp(value, 12, 20))} />
                  <NumberSlider label={t('editorPanel.metaSize')} min={10} max={14} value={guidance.metaFontSizePx} suffix="px" onChange={(value) => updateGuidance('metaFontSizePx', clamp(value, 10, 14))} />
                  <NumberSlider label={t('editorPanel.bodySize')} min={11} max={15} value={guidance.bodyFontSizePx} suffix="px" onChange={(value) => updateGuidance('bodyFontSizePx', clamp(value, 11, 15))} />
                  <NumberSlider label={t('editorPanel.lineHeight')} min={140} max={185} value={guidance.lineHeightPercent} suffix="%" onChange={(value) => updateGuidance('lineHeightPercent', clamp(value, 140, 185))} />
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.bodyTextColor')}</span>
                    <input type="color" value={guidance.bodyTextColor} onChange={(e) => updateGuidance('bodyTextColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.bodyTextColor}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.metaTextColor')}</span>
                    <input type="color" value={guidance.metaTextColor} onChange={(e) => updateGuidance('metaTextColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.metaTextColor}</span>
                  </div>
                  <NumberSlider label={t('editorPanel.contactGap')} min={2} max={8} value={guidance.contactGapPx} suffix="px" onChange={(value) => updateGuidance('contactGapPx', clamp(value, 2, 8))} />
                  <NumberSlider label={t('editorPanel.roleMarginTop')} min={2} max={14} value={guidance.roleMarginTopPx} suffix="px" onChange={(value) => updateGuidance('roleMarginTopPx', clamp(value, 2, 14))} />
                  <NumberSlider label={t('editorPanel.headerPadBtm')} min={4} max={20} value={guidance.headerPaddingBottomPx} suffix="px" onChange={(value) => updateGuidance('headerPaddingBottomPx', clamp(value, 4, 20))} />
                  <NumberSlider label={t('editorPanel.headerMarginBtm')} min={8} max={28} value={guidance.headerMarginBottomPx} suffix="px" onChange={(value) => updateGuidance('headerMarginBottomPx', clamp(value, 8, 28))} />
                  <NumberSlider label={t('editorPanel.dividerThick')} min={0} max={4} value={guidance.headerDividerThicknessPx} suffix="px" onChange={(value) => updateGuidance('headerDividerThicknessPx', clamp(value, 0, 4))} />
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.accentColor')}</span>
                    <input type="color" value={guidance.accentColor} onChange={(e) => updateGuidance('accentColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.accentColor}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.dividerColor')}</span>
                    <input type="color" value={guidance.headerDividerColor} onChange={(e) => updateGuidance('headerDividerColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.headerDividerColor}</span>
                  </div>
                </div>
              ) : null}

              {activeGroup === 'layout' ? (
                <div className="space-y-3">
                  <h4 className="font-mono text-[11px] font-bold uppercase tracking-wider text-[var(--brand-signal)]">{t('editorPanel.layout')}</h4>
                  <SelectorButtons<ColumnMode>
                    label={t('editorPanel.columnMode')}
                    value={guidance.columnMode}
                    onChange={(value) => updateGuidance('columnMode', value)}
                    options={columnModeOptions}
                  />
                  <SelectorButtons<'inline' | 'stacked'>
                    label={t('editorPanel.contactLayout')}
                    value={guidance.contactLayout}
                    onChange={(value) => updateGuidance('contactLayout', value)}
                    options={[
                      { value: 'inline' as const, text: t('editorPanel.inline') },
                      { value: 'stacked' as const, text: t('editorPanel.stacked') },
                    ]}
                  />
                  <NumberSlider label={t('editorPanel.leftColumn')} min={24} max={42} value={guidance.leftWidthPercent} suffix="%" onChange={(value) => updateGuidance('leftWidthPercent', clamp(value, 24, 42))} />
                  <NumberSlider label={t('editorPanel.columnGap')} min={10} max={28} value={guidance.columnGapPx} suffix="px" onChange={(value) => updateGuidance('columnGapPx', clamp(value, 10, 28))} />
                  <NumberSlider label={t('editorPanel.sidebarPadding')} min={0} max={18} value={guidance.sidebarPaddingPx} suffix="px" onChange={(value) => updateGuidance('sidebarPaddingPx', clamp(value, 0, 18))} />
                  <NumberSlider label={t('editorPanel.sidebarRadius')} min={0} max={12} value={guidance.sidebarRadiusPx} suffix="px" onChange={(value) => updateGuidance('sidebarRadiusPx', clamp(value, 0, 12))} />
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.sidebarBg')}</span>
                    <input type="color" value={guidance.leftSidebarBg} onChange={(e) => updateGuidance('leftSidebarBg', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <button type="button" onClick={() => updateGuidance('leftSidebarBg', '#fafafa')} className="font-mono text-[10px] border border-gray-300 dark:border-[var(--brand-line)] px-1.5 py-0.5 hover:bg-gray-100 dark:hover:bg-[var(--brand-surface-soft)]">{t('editorPanel.reset')}</button>
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.leftSidebarBg}</span>
                  </div>
                </div>
              ) : null}

              {activeGroup === 'sections' ? (
                <div className="space-y-3">
                  <h4 className="font-mono text-[11px] font-bold uppercase tracking-wider text-[var(--brand-signal)]">{t('editorPanel.headingAndLists')}</h4>
                  <SelectorButtons<SectionHeadingStyle>
                    label={t('editorPanel.headingStyle')}
                    value={guidance.sectionHeadingStyle}
                    onChange={(value) => updateGuidance('sectionHeadingStyle', value)}
                    options={headingStyleOptions}
                  />
                  <SelectorButtons<SectionHeadingCase>
                    label={t('editorPanel.headingCase')}
                    value={guidance.sectionHeadingCase}
                    onChange={(value) => updateGuidance('sectionHeadingCase', value)}
                    options={headingCaseOptions}
                  />
                  <NumberSlider label={t('editorPanel.headingSize')} min={11} max={16} value={guidance.sectionHeadingSizePx} suffix="px" onChange={(value) => updateGuidance('sectionHeadingSizePx', clamp(value, 11, 16))} />
                  <NumberSlider label={t('editorPanel.headingRuleGap')} min={0} max={10} value={guidance.sectionUnderlineGapPx} suffix="px" onChange={(value) => updateGuidance('sectionUnderlineGapPx', clamp(value, 0, 10))} />
                  <NumberSlider label={t('editorPanel.headingRuleThick')} min={0} max={3} step={0.5} value={guidance.sectionUnderlineThicknessPx} suffix="px" onChange={(value) => updateGuidance('sectionUnderlineThicknessPx', clamp(value, 0, 3))} />
                  <SelectorButtons<DateStyle>
                    label={t('editorPanel.datePosition')}
                    value={guidance.dateStyle}
                    onChange={(value) => updateGuidance('dateStyle', value)}
                    options={dateStyleOptions}
                  />
                  <SelectorButtons<BulletStyle>
                    label={t('editorPanel.bulletStyle')}
                    value={guidance.bulletStyle}
                    onChange={(value) => updateGuidance('bulletStyle', value)}
                    options={bulletStyleOptions}
                  />
                  <SelectorButtons<ListLayoutMode>
                    label={t('editorPanel.skillsLayout')}
                    value={guidance.skillsLayout}
                    onChange={(value) => updateGuidance('skillsLayout', value)}
                    options={layoutOptions}
                  />
                  <SelectorButtons<ListLayoutMode>
                    label={t('editorPanel.languagesLayout')}
                    value={guidance.languagesLayout}
                    onChange={(value) => updateGuidance('languagesLayout', value)}
                    options={layoutOptions}
                  />
                  <SelectorButtons<ListLayoutMode>
                    label={t('editorPanel.certLayout')}
                    value={guidance.certificationsLayout}
                    onChange={(value) => updateGuidance('certificationsLayout', value)}
                    options={layoutOptions}
                  />
                  <SelectorButtons<ListLayoutMode>
                    label={t('editorPanel.awardsLayout')}
                    value={guidance.awardsLayout}
                    onChange={(value) => updateGuidance('awardsLayout', value)}
                    options={layoutOptions}
                  />
                  <NumberSlider label={t('editorPanel.tagFontSize')} min={8} max={14} value={guidance.tagFontSizePx} suffix="px" onChange={(value) => updateGuidance('tagFontSizePx', clamp(value, 8, 14))} />
                  <NumberSlider label={t('editorPanel.tagGap')} min={2} max={12} value={guidance.tagGapPx} suffix="px" onChange={(value) => updateGuidance('tagGapPx', clamp(value, 2, 12))} />
                  <NumberSlider label={t('editorPanel.tagPaddingX')} min={2} max={14} value={guidance.tagPaddingXPx} suffix="px" onChange={(value) => updateGuidance('tagPaddingXPx', clamp(value, 2, 14))} />
                  <NumberSlider label={t('editorPanel.tagPaddingY')} min={0} max={8} value={guidance.tagPaddingYPx} suffix="px" onChange={(value) => updateGuidance('tagPaddingYPx', clamp(value, 0, 8))} />
                  <NumberSlider label={t('editorPanel.tagRadius')} min={0} max={18} value={guidance.tagRadiusPx} suffix="px" onChange={(value) => updateGuidance('tagRadiusPx', clamp(value, 0, 18))} />
                  <NumberSlider label={t('editorPanel.tagBorderWidth')} min={0} max={2} step={0.5} value={guidance.tagBorderWidthPx} suffix="px" onChange={(value) => updateGuidance('tagBorderWidthPx', clamp(value, 0, 2))} />
                  <NumberSlider label={t('editorPanel.bulletIndent')} min={10} max={30} value={guidance.bulletIndentPx} suffix="px" onChange={(value) => updateGuidance('bulletIndentPx', clamp(value, 10, 30))} />
                  <NumberSlider label={t('editorPanel.bulletListTopGap')} min={0} max={10} value={guidance.bulletListTopGapPx} suffix="px" onChange={(value) => updateGuidance('bulletListTopGapPx', clamp(value, 0, 10))} />
                  <NumberSlider label={t('editorPanel.bulletItemGap')} min={2} max={12} value={guidance.bulletItemGapPx} suffix="px" onChange={(value) => updateGuidance('bulletItemGapPx', clamp(value, 2, 12))} />
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.tagBorder')}</span>
                    <input type="color" value={guidance.tagBorderColor} onChange={(e) => updateGuidance('tagBorderColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.tagBorderColor}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-28 font-sans text-xs text-gray-500 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.tagBg')}</span>
                    <input type="color" value={guidance.tagBgColor} onChange={(e) => updateGuidance('tagBgColor', e.target.value)} className="h-6 w-8 cursor-pointer border border-gray-300 dark:border-[var(--brand-line)]" />
                    <span className="font-mono text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)]">{guidance.tagBgColor}</span>
                  </div>
                  <label className="mt-2 flex cursor-pointer items-center gap-3">
                    <button
                      type="button"
                      onClick={() => updateGuidance('showHeaderDivider', !guidance.showHeaderDivider)}
                      className={`relative h-5 w-10 border-2 transition-all ${
                        guidance.showHeaderDivider ? 'border-[var(--brand-signal)] bg-[var(--brand-signal)]' : 'border-gray-400 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)]'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 h-3.5 w-3.5 border bg-white dark:bg-zinc-200 transition-all ${
                          guidance.showHeaderDivider ? 'left-5 border-[var(--brand-signal)]' : 'left-0.5 border-gray-400 dark:border-[var(--brand-line)]'
                        }`}
                      />
                    </button>
                    <span className="font-mono text-xs uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">{t('editorPanel.headerDivider')}</span>
                  </label>
                </div>
              ) : null}
            </div>

            <div className="space-y-2 border-t border-gray-200 dark:border-[var(--brand-line)] pt-3">
              <h4 className="font-mono text-[11px] font-bold uppercase tracking-wider text-gray-600 dark:text-[var(--brand-ink-muted)]">{t('editorPanel.sectionOrder')}</h4>
              {guidance.columnMode === 'double' && (
                <p className="font-mono text-[9px] uppercase tracking-wide text-[var(--brand-signal)]">
                  {t('editorPanel.columnSwitchHint')}
                </p>
              )}
              <div className="space-y-1">
                {(sections || []).map((item, index) => (
                  <div key={item.id} className="flex items-center gap-2 border border-[var(--brand-line)]/20 bg-white dark:bg-[var(--brand-surface)] px-2 py-1.5">
                    <button
                      type="button"
                      onClick={() => toggleSection(index)}
                      className={`h-4 w-4 border ${item.visible ? 'border-[var(--brand-signal)] bg-[var(--brand-signal)]' : 'border-[var(--brand-line)]/40 bg-white dark:bg-[var(--brand-surface)]'}`}
                      title={item.visible ? t('editorPanel.hideSection') : t('editorPanel.showSection')}
                    />
                    {guidance.columnMode === 'double' && (
                      <button
                        type="button"
                        onClick={() => toggleColumn(index)}
                        className={`font-mono text-[10px] px-1.5 py-0.5 border font-bold transition-colors ${
                          item.column === 'left'
                            ? 'border-blue-400 dark:border-blue-500/60 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                            : 'border-gray-300 dark:border-[var(--brand-line)] bg-gray-50 dark:bg-[var(--brand-surface-soft)] text-gray-500 dark:text-[var(--brand-ink-muted)] hover:border-blue-300 dark:hover:border-blue-500/40'
                        }`}
                        title={item.column === 'left' ? t('editorPanel.leftColumnTooltip') : t('editorPanel.rightColumnTooltip')}
                      >
                        {item.column === 'left' ? '\u2B05' : '\u27A1'}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => cyclePage(index)}
                      className="font-mono text-[10px] px-1.5 py-0.5 border border-gray-300 dark:border-[var(--brand-line)] bg-gray-50 dark:bg-[var(--brand-surface-soft)] text-gray-500 dark:text-[var(--brand-ink-muted)] hover:border-[var(--brand-signal)] transition-colors font-bold"
                      title={t('editorPanel.pageNumber', { page: item.page ?? 1 })}
                    >
                      P{item.page ?? 1}
                    </button>
                    <span className="min-w-0 flex-1 truncate font-mono text-[10px] uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">{item.title}</span>
                    <button type="button" onClick={() => moveSection(index, -1)} disabled={index === 0} className="border border-[var(--brand-line)]/30 px-1.5 py-0.5 font-mono text-[10px] disabled:opacity-40">↑</button>
                    <button
                      type="button"
                      onClick={() => moveSection(index, 1)}
                      disabled={index === sections.length - 1}
                      className="border border-[var(--brand-line)]/30 px-1.5 py-0.5 font-mono text-[10px] disabled:opacity-40"
                    >
                      ↓
                    </button>
                  </div>
                ))}
              </div>
              <Button variant="outline" size="sm" className="w-full" onClick={() => onGuidanceChange({ ...DEFAULT_GUIDANCE })}>
                <RotateCcw className="size-3" />
                {t('editorPanel.resetGuidance')}
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
