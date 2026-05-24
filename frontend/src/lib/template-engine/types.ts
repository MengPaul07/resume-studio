/** A template definition — JSON-driven, renderer-agnostic. */

export interface TypeScaleEntry {
  size: number;
  weight: 'normal' | 'bold';
  color: string | null;
  case: 'none' | 'uppercase';
  /** CSS letter-spacing hint */
  tracking?: 'wide';
}

export type TypeScale = Record<string, TypeScaleEntry>;

export interface TemplateField {
  /** Path into resume JSON. Relative to section key for array items, absolute for single sections. */
  path: string;
  /** Key into type_scale */
  tier: string;
  /** Render inline with preceding field (same line) */
  inline?: boolean;
  /** Value is an array — render each item as a bullet */
  bullet?: boolean;
  /** Separator between inline fields */
  separator?: string;
  /** Text prepended before the value (e.g. "GPA: ") */
  prefix?: string;
  /** Override tier color */
  color?: 'muted' | null;
  /** Hide the line if value is empty (default: true) */
  hide_empty?: boolean;
}

export interface TemplateSection {
  /** Key into resumeObj to get this section's data */
  key: string;
  /** Display title (null = no title row) */
  title: string | null;
  /** Layout mode */
  type: 'single' | 'array' | 'key_value';
  /** Key into type_scale for the section title */
  title_tier?: string;
  /** Margin between array items: sm | md | lg */
  item_spacing?: 'sm' | 'md' | 'lg';

  /** For type=single: flat field list. For type=array: fields per array item. */
  fields: TemplateField[];
  /** For type=array: the item-level field list (alternative to top-level fields for clarity) */
  item?: { fields: TemplateField[] };
  /** For type=key_value: layout variant */
  layout?: 'inline_tags' | 'list';
}

export interface TemplateDefinition {
  template_id: string;
  display_name: string;
  doc_type: string;
  page: {
    format: 'a4' | 'letter';
    margin: string;
    columns: number;
  };
  type_scale: TypeScale;
  sections: TemplateSection[];
}
