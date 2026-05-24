"""
Preset field-name mappings for automatic alignment.
When JSON uses a non-standard field name that maps to a known template slot,
these mappings let the backend fix it without LLM involvement.
"""
from typing import Any, Dict, List

# source_path -> target_path, with optional transform hint
FIELD_ALIASES: Dict[str, Dict[str, str]] = {
    # education
    "education.field": {"target": "education.degree", "transform": "direct"},
    "education.major": {"target": "education.degree", "transform": "direct"},
    "education.school": {"target": "education.institution", "transform": "direct"},
    "education.university": {"target": "education.institution", "transform": "direct"},
    "education.graduation": {"target": "education.years", "transform": "direct"},
    "education.startDate": {"target": "education.years", "transform": "direct"},
    "education.endDate": {"target": "education.years", "transform": "direct"},
    "education.courses": {"target": "education.description", "transform": "join_list"},
    "education.achievements": {"target": "education.description", "transform": "join_list"},
    "education.details": {"target": "education.description", "transform": "join_list"},
    "education.gpa": {"target": "education.description", "transform": "wrap_text"},
    # personalProjects
    "personalProjects.title": {"target": "personalProjects.name", "transform": "direct"},
    "personalProjects.position": {"target": "personalProjects.role", "transform": "direct"},
    "personalProjects.technologies": {"target": "personalProjects.description", "transform": "join_list"},
    "personalProjects.projectDescription": {"target": "personalProjects.description", "transform": "join_list"},
    "personalProjects.details": {"target": "personalProjects.description", "transform": "join_list"},
    "personalProjects.website": {"target": "personalProjects.description", "transform": "wrap_text"},
    "personalProjects.github": {"target": "personalProjects.description", "transform": "wrap_text"},
    "personalProjects.url": {"target": "personalProjects.website", "transform": "direct"},
    "personalProjects.link": {"target": "personalProjects.website", "transform": "direct"},
    "personalProjects.startDate": {"target": "personalProjects.years", "transform": "direct"},
    "personalProjects.endDate": {"target": "personalProjects.years", "transform": "direct"},
    "personalProjects.duration": {"target": "personalProjects.years", "transform": "direct"},
    # workExperience
    "workExperience.position": {"target": "workExperience.title", "transform": "direct"},
    "workExperience.role": {"target": "workExperience.title", "transform": "direct"},
    "workExperience.organization": {"target": "workExperience.company", "transform": "direct"},
    "workExperience.employer": {"target": "workExperience.company", "transform": "direct"},
    "workExperience.office": {"target": "workExperience.location", "transform": "direct"},
    "workExperience.duration": {"target": "workExperience.years", "transform": "direct"},
    "workExperience.startDate": {"target": "workExperience.years", "transform": "direct"},
    "workExperience.endDate": {"target": "workExperience.years", "transform": "direct"},
    "workExperience.responsibilities": {"target": "workExperience.description", "transform": "join_list"},
    "workExperience.details": {"target": "workExperience.description", "transform": "join_list"},
    "workExperience.achievements": {"target": "workExperience.description", "transform": "join_list"},
    # additional
    "additional.skills": {"target": "additional.technicalSkills", "transform": "split_to_list"},
    "additional.technologies": {"target": "additional.technicalSkills", "transform": "split_to_list"},
    "additional.certifications": {"target": "additional.certificationsTraining", "transform": "direct"},
    "additional.certification": {"target": "additional.certificationsTraining", "transform": "direct"},
    "additional.honors": {"target": "additional.awards", "transform": "direct"},
    "additional.language": {"target": "additional.languages", "transform": "split_to_list"},
    # personalInfo
    "personalInfo.jobTitle": {"target": "personalInfo.title", "transform": "direct"},
    "personalInfo.fullName": {"target": "personalInfo.name", "transform": "direct"},
    "personalInfo.emailAddress": {"target": "personalInfo.email", "transform": "direct"},
    "personalInfo.phoneNumber": {"target": "personalInfo.phone", "transform": "direct"},
    "personalInfo.address": {"target": "personalInfo.location", "transform": "direct"},
    "personalInfo.url": {"target": "personalInfo.website", "transform": "direct"},
    "personalInfo.web": {"target": "personalInfo.website", "transform": "direct"},
    "personalInfo.linkedIn": {"target": "personalInfo.linkedin", "transform": "direct"},
    "personalInfo.gitHub": {"target": "personalInfo.github", "transform": "direct"},
}

# Sections known to standard templates
STANDARD_SECTIONS: Dict[str, List[str]] = {
    "personalInfo": ["name", "title", "email", "phone", "location", "website", "linkedin", "github"],
    "summary": ["summary"],
    "workExperience": ["title", "company", "location", "years", "description"],
    "education": ["institution", "degree", "years", "description"],
    "personalProjects": ["name", "role", "years", "description", "github", "website"],
    "research": ["name", "role", "institution", "years", "description"],
    "additional": ["technicalSkills", "languages", "certificationsTraining", "awards"],
}

# Fields that backend handles directly (LLM should not touch these)
SIMPLE_RENDER_FIELDS: set[str] = {
    "personalInfo.name", "personalInfo.email", "personalInfo.phone",
    "personalInfo.location", "personalInfo.website", "personalInfo.linkedin",
    "personalInfo.github", "personalInfo.title",
}


def lookup_alias(json_path: str) -> Dict[str, str] | None:
    """Return {target, transform} if json_path has a known alias."""
    return FIELD_ALIASES.get(json_path)


def is_simple_field(path: str) -> bool:
    return path in SIMPLE_RENDER_FIELDS
