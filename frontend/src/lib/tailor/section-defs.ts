/**
 * Field alias definitions for resume sections.
 * Mirrors SECTION_RENDER_DEFS in layout_design/nodes/common.py.
 * Kept in sync manually — both sides define the same canonical fields and aliases.
 */

export const SECTION_FIELD_ALIASES: Record<string, Record<string, string[]>> = {
  personalInfo: {
    name:          ['name', 'fullName'],
    title:         ['title', 'jobTitle'],
    email:         ['email', 'emailAddress'],
    phone:         ['phone', 'phoneNumber'],
    location:      ['location', 'address'],
    website:       ['website', 'url', 'web'],
    linkedin:      ['linkedin', 'linkedIn'],
    github:        ['github', 'gitHub'],
  },
  workExperience: {
    title:         ['title', 'position', 'role'],
    company:       ['company', 'organization', 'employer'],
    location:      ['location', 'office'],
    years:         ['years', 'date', 'period', 'duration', 'startDate', 'endDate'],
    description:   ['description', 'details', 'summary', 'responsibilities', 'achievements'],
  },
  education: {
    institution:   ['institution', 'school', 'university'],
    degree:        ['degree', 'field', 'major'],
    years:         ['years', 'date', 'period', 'graduation', 'startDate', 'endDate'],
    gpa:           ['gpa'],
    description:   ['description', 'details', 'summary', 'achievements', 'courses'],
  },
  personalProjects: {
    name:          ['name', 'title', 'projectName'],
    role:          ['role', 'position'],
    years:         ['years', 'date', 'period', 'duration', 'startDate', 'endDate'],
    description:   ['description', 'projectDescription', 'summary', 'details', 'technologies'],
    github:        ['github'],
    website:       ['website', 'url', 'link'],
  },
  additional: {
    technicalSkills:        ['technicalSkills', 'skills', 'technologies'],
    languages:              ['languages', 'language'],
    certificationsTraining: ['certificationsTraining', 'certifications', 'certification'],
    awards:                 ['awards', 'honors'],
  },
  research: {
    name:          ['name', 'title', 'projectName', 'topic'],
    role:          ['role', 'position'],
    institution:   ['institution', 'school', 'university', 'lab'],
    years:         ['years', 'date', 'period', 'duration', 'startDate', 'endDate'],
    description:   ['description', 'summary', 'achievements', 'publications', 'findings'],
  },
};

/**
 * Resolve a field value using its alias chain.
 * Returns the first non-empty value found in the aliases list.
 */
export function resolveFieldValue(
  item: Record<string, unknown>,
  section: string,
  fieldName: string,
): unknown {
  const sectionDef = SECTION_FIELD_ALIASES[section];
  if (!sectionDef) return item[fieldName];
  const aliases = sectionDef[fieldName];
  if (!aliases) return item[fieldName];
  for (const alias of aliases) {
    const v = item[alias];
    if (v !== undefined && v !== null && v !== '') return v;
  }
  return undefined;
}
