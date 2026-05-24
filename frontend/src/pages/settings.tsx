import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { testLLMConnectivity } from '../api';
import { PageTransition } from '../components/layout/page-transition';
import { Button } from '../components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import {
  DEFAULT_LLM_CONFIG,
  findPresetIdByConfig,
  getPresetById,
  groupPresetsByProvider,
  loadLLMConfig,
  resetLLMConfig,
  saveLLMConfig,
  type LLMConfig,
} from '../llm-settings';

function isSameLLMConfig(a: LLMConfig, b: LLMConfig): boolean {
  return (
    a.model === b.model &&
    a.api_key === b.api_key &&
    a.api_base === b.api_base &&
    a.max_tokens === b.max_tokens &&
    a.temperature === b.temperature
  );
}

export function SettingsPage() {
  const { t } = useTranslation();
  const [savedConfig, setSavedConfig] = useState<LLMConfig>(() => loadLLMConfig());
  const [draft, setDraft] = useState<LLMConfig>(savedConfig);
  const [savedAt, setSavedAt] = useState<string>('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string>('');
  const [testError, setTestError] = useState<string>('');
  const [customModel, setCustomModel] = useState<string>('');

  const selectedPresetId = useMemo(() => {
    // If customModel is set (user typed something), don't match a preset
    if (customModel) return '';
    return findPresetIdByConfig(draft);
  }, [draft, customModel]);
  const groupedPresets = useMemo(() => groupPresetsByProvider(), []);
  const isDirty = !isSameLLMConfig(draft, savedConfig);

  const updateField = <K extends keyof LLMConfig>(key: K, value: LLMConfig[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    saveLLMConfig(draft);
    setSavedConfig(draft);
    setSavedAt(new Date().toLocaleTimeString());
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult('');
    setTestError('');
    try {
      const data = await testLLMConnectivity({ llm_config: draft as Record<string, unknown> });
      if (!data.ok) setTestError(data.message || 'Connectivity test failed.');
      else setTestResult(`OK | ${data.model} | ${data.latency_ms}ms | ${data.provider_response_preview || 'No preview'}`);
    } catch (error) {
      setTestError(error instanceof Error ? error.message : 'Connectivity test failed.');
    } finally {
      setTesting(false);
    }
  };

  const handleReset = () => {
    const defaults = resetLLMConfig();
    setDraft(defaults);
    setSavedConfig(defaults);
    setSavedAt('');
    setCustomModel('');
  };

  const handlePresetChange = (presetId: string) => {
    const preset = getPresetById(presetId);
    if (!preset) return;
    setCustomModel('');
    setDraft((prev) => ({
      ...prev,
      model: preset.model,
      api_base: preset.api_base || prev.api_base,
      max_tokens: preset.max_tokens,
      temperature: preset.temperature,
    }));
  };

  const handleCustomModelChange = (value: string) => {
    setCustomModel(value);
    setDraft((prev) => ({ ...prev, model: value }));
  };

  return (
    <PageTransition>
      <section className="mx-auto max-w-[86rem] px-4 py-8">
        <div className="border border-black dark:border-zinc-600 bg-canvas shadow-[8px_8px_0px_0px_#000000] dark:shadow-[8px_8px_0px_0px_#333333]">
          <div className="border-b border-black dark:border-zinc-600 p-6 md:p-8">
            <h1 className="font-serif text-5xl uppercase leading-none">{t('settings.title')}</h1>
            <p className="mt-2 font-mono text-xs uppercase text-[var(--brand-signal)]">{t('settings.subtitle')}</p>
          </div>

          <div className="grid grid-cols-1 gap-[1px] bg-black dark:bg-zinc-600 md:grid-cols-2">
            <div className="space-y-2 bg-background p-4">
              <Card variant="interactive">
                <CardHeader>
                  <CardTitle className="uppercase">{t('settings.llmProvider')}</CardTitle>
                  <CardDescription>{t('settings.llmProviderDesc')}</CardDescription>
                </CardHeader>
                <div className="space-y-2">
                  <select value={selectedPresetId} onChange={(e) => handlePresetChange(e.target.value)} className="ui-input">
                    {!selectedPresetId ? <option value="">{t('settings.custom')}</option> : null}
                    {groupedPresets.map((group) => (
                      <optgroup key={group.provider} label={group.provider}>
                        {group.items.map((preset) => (
                          <option key={preset.id} value={preset.id}>
                            {preset.name}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                  <input
                    value={customModel}
                    onChange={(e) => handleCustomModelChange(e.target.value)}
                    placeholder={t('settings.directModelPlaceholder')}
                    className="ui-input"
                  />
                  <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--brand-ink-muted)]">{t('settings.directModelInput')}</p>
                  <input value={draft.api_key} onChange={(e) => updateField('api_key', e.target.value)} placeholder="api_key" type="password" className="ui-input" />
                  {customModel ? (
                    <input
                      value={draft.api_base}
                      onChange={(e) => updateField('api_base', e.target.value)}
                      placeholder={t('settings.apiBase')}
                      className="ui-input"
                    />
                  ) : (
                    <div className="rounded-xl border border-[var(--brand-line-strong)] bg-[var(--brand-surface)] px-3 py-2">
                      <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--brand-ink-muted)]">{t('settings.apiBase')}</p>
                      <p className="mt-1 font-mono text-xs">{draft.api_base}</p>
                    </div>
                  )}
                  <div className="rounded-xl border border-[var(--brand-line-strong)] bg-[var(--brand-surface)] px-3 py-2">
                    <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--brand-ink-muted)]">Model</p>
                    <p className="mt-1 font-mono text-xs">{draft.model}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      value={String(draft.max_tokens)}
                      onChange={(e) => updateField('max_tokens', Number(e.target.value) || DEFAULT_LLM_CONFIG.max_tokens)}
                      placeholder={t('settings.maxTokens')}
                      type="number"
                      min={1}
                      className="ui-input"
                    />
                    <input
                      value={String(draft.temperature)}
                      onChange={(e) => updateField('temperature', Number(e.target.value))}
                      placeholder={t('settings.temperature')}
                      type="number"
                      step="0.1"
                      className="ui-input"
                    />
                  </div>
                </div>
              </Card>

              <Card variant="interactive">
                <CardHeader>
                  <CardTitle className="uppercase">{t('settings.modelCatalog')}</CardTitle>
                  <CardDescription>{t('settings.modelCatalogDesc')}</CardDescription>
                </CardHeader>
                <div className="space-y-2">
                  {groupedPresets.map((group) => (
                    <div key={group.provider} className="rounded-lg border border-[var(--brand-line)] bg-[var(--brand-paper)] p-2">
                      <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--brand-ink-muted)]">{group.provider}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {group.items.map((preset) => (
                          <span
                            key={preset.id}
                            className={`rounded-lg border px-2 py-1 font-mono text-[10px] uppercase tracking-wide ${
                              preset.id === selectedPresetId
                                ? 'border-[var(--brand-signal)] bg-[var(--brand-signal-soft)] text-[var(--brand-signal)]'
                                : 'border-[var(--brand-line)] bg-[var(--brand-paper)] text-[var(--brand-ink-muted)]'
                            }`}
                          >
                            {preset.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card variant="interactive">
                <CardHeader>
                  <CardTitle className="uppercase">{t('settings.connectivityTest')}</CardTitle>
                  <CardDescription>{t('settings.connectivityTestDesc')}</CardDescription>
                </CardHeader>
                <div className="space-y-2">
                  <Button onClick={handleTestConnection} disabled={testing} className="w-full">
                    {testing ? t('settings.testing') : t('settings.testApi')}
                  </Button>
                  {testResult ? <p className="border border-black dark:border-zinc-600 bg-canvas p-2 font-mono text-xs">{testResult}</p> : null}
                  {testError ? <p className="border border-black dark:border-zinc-600 bg-[#ffe3e3] dark:bg-red-950 p-2 font-mono text-xs text-[var(--status-failed)]">{testError}</p> : null}
                </div>
              </Card>
            </div>

            <div className="flex flex-col justify-between bg-[var(--brand-surface-soft)] p-6 md:p-8">
              <div>
                <h2 className="font-serif text-3xl uppercase">{t('settings.systemStatus')}</h2>
                <div className="mt-4 grid grid-cols-2 gap-2 font-mono text-xs uppercase">
<div className="border border-black dark:border-zinc-600 bg-canvas p-3">{t('settings.llm')}: {draft.model || 'N/A'}</div>
                  <div className="border border-black dark:border-zinc-600 bg-canvas p-3">{t('settings.parserReady')}</div>
                  <div className="border border-black dark:border-zinc-600 bg-canvas p-3">{t('settings.pdfReady')}</div>
                  <div className="border border-black dark:border-zinc-600 bg-canvas p-3">{t('settings.saved')}: {savedAt || t('settings.no')}</div>
                </div>
              </div>
              <div className="mt-8 flex gap-2">
                <Button variant="outline" onClick={handleReset}>{t('settings.reset')}</Button>
                <Button onClick={handleSave} disabled={!isDirty}>{t('settings.saveSettings')}</Button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </PageTransition>
  );
}
