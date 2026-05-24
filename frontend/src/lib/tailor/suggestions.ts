import type { SuggestionItem } from '../../types';
import type { ChangeVariant, PendingChange } from './types';

export function getSuggestionItemsFromTurn(turn: {
  turn_output_bundle?: { suggestion_document_obj?: { items?: SuggestionItem[] } };
  suggestion_document_obj?: { items?: SuggestionItem[] };
  suggestion_resume_obj?: { items?: SuggestionItem[] };
}): SuggestionItem[] {
  const bundleItems = turn.turn_output_bundle?.suggestion_document_obj?.items;
  const fromSuggestion: SuggestionItem[] = Array.isArray(bundleItems)
    ? bundleItems
    : Array.isArray(turn.suggestion_document_obj?.items)
      ? (turn.suggestion_document_obj.items as SuggestionItem[])
    : Array.isArray(turn.suggestion_resume_obj?.items)
      ? (turn.suggestion_resume_obj.items as SuggestionItem[])
    : [];
  if (fromSuggestion.length) {
    return fromSuggestion
      .filter((item) => Boolean(item?.path))
      .map((item) => ({
        section: item.section,
        path: item.path,
        op: item.op,
        item_key: item.item_key,
        status: item.status,
        current_value: item.current_value,
        suggested_value: item.suggested_value,
        reason: item.reason,
        current_value_raw: item.current_value_raw,
        suggested_value_raw: item.suggested_value_raw,
        refined_text: item.refined_text,
        refined_value_raw: item.refined_value_raw,
        suggestion: item.suggestion,
        option_id: item.option_id,
        option_label: item.option_label,
        actionability: item.actionability,
        requires_confirmation: item.requires_confirmation,
        confirmation_hint: item.confirmation_hint,
        confidence: item.confidence,
        confidence_reason: item.confidence_reason,
        low_confidence: item.low_confidence,
        style_variant: item.style_variant,
        reason_meta: item.reason_meta,
        diff_payload: item.diff_payload,
      }));
  }
  return [];
}

export function isApplyReadyItem(item: SuggestionItem): boolean {
  if (item.requires_confirmation === true) return false;
  const tag = String(item.actionability || '').toLowerCase();
  if (tag === 'confirm_required') return false;
  if (tag === 'apply_ready') return true;
  return true;
}

export function suggestionItemKey(item: SuggestionItem): string {
  const explicit = String(item.item_key || '').trim();
  if (explicit) return explicit;
  return `${item.path}::${String(item.option_id || 'default')}`;
}

export function suggestionItemsToPendingChanges(items: SuggestionItem[]): PendingChange[] {
  const applyReady = items.filter((item) => isApplyReadyItem(item));
  const groups = new Map<string, SuggestionItem[]>();
  for (const item of applyReady) {
    const existing = groups.get(item.path) || [];
    existing.push(item);
    groups.set(item.path, existing);
  }
  const result: PendingChange[] = [];
  for (const [path, groupItems] of groups) {
    const first = groupItems[0];
    const variants: ChangeVariant[] = groupItems.map((item) => ({
      suggested_value: item.suggested_value,
      reason: item.reason,
      option_id: item.option_id || '',
      option_label: item.option_label || '',
      style_variant: item.style_variant,
    }));
    result.push({
      path,
      section: first.section,
      current_value: first.current_value,
      item_key: suggestionItemKey(first),
      op: first.op,
      lowConfidence: first.low_confidence === true,
      confidence: first.confidence,
      confidenceReason: first.confidence_reason,
      diff_payload: first.diff_payload as PendingChange['diff_payload'],
      variants,
    });
  }
  return result;
}

export function buildAssistantReplyText(
  userPrompt: string,
  assistantMessage: string,
  changes: PendingChange[],
): string {
  void userPrompt;
  void changes;
  return (assistantMessage || '').trim() || '已完成本轮处理。';
}
