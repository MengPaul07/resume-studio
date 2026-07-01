/** Sample resume — shown on first visit when localStorage is empty. */
export const SAMPLE_RESUME = {
  personalInfo: {
    name: "Alex Chen",
    title: "Senior Full-Stack Engineer",
    email: "alex.chen@example.com",
    phone: "555-0123",
    location: "San Francisco, CA",
    github: "github.com/alexchen",
    linkedin: "linkedin.com/in/alexchen",
  },
  summary: "Full-stack engineer with 6 years of experience building B2B SaaS products. Led 3 major platform launches serving 500K+ users. Proficient in React, TypeScript, Node.js, and AWS. Passionate about developer experience and design systems.",
  workExperience: [
    {
      title: "Senior Software Engineer",
      company: "Stripe",
      location: "San Francisco, CA",
      years: "2022-03 to present",
      description: [
        "Built the billing analytics dashboard serving 10K+ enterprise customers, processing $2B+ annual transaction data",
        "Led migration from REST to GraphQL, reducing API response size by 45% and improving page load time by 60%",
        "Mentored 3 junior engineers through structured onboarding and code review",
      ],
    },
    {
      title: "Full-Stack Engineer",
      company: "Asana",
      location: "San Francisco, CA",
      years: "2019-07 to 2022-02",
      description: [
        "Built real-time collaborative editing features used by 100K+ teams",
        "Improved WebSocket sync latency by 30% through connection pooling and message batching",
        "Shipped 12 major features across 4 quarterly release cycles",
      ],
    },
  ],
  education: [
    {
      institution: "University of California, Berkeley",
      degree: "B.S. Computer Science",
      years: "2015-09 to 2019-05",
      gpa: "3.7/4.0",
      description: ["Dean's List (4 semesters). Teaching assistant for CS 61A."],
    },
  ],
  personalProjects: [
    {
      name: "DevFlow",
      role: "Creator",
      years: "2023",
      description: [
        "CI/CD visualization tool for monorepos with 800+ GitHub stars",
        "Featured in GitHub trending weekly (July 2023)",
      ],
    },
  ],
  research: [],
  additional: {
    technicalSkills: [
      "React", "TypeScript", "Node.js", "GraphQL", "PostgreSQL",
      "AWS (Lambda, RDS, ECS)", "Redis", "Docker", "Terraform", "Datadog",
    ],
    languages: ["English (Native)", "Spanish (Conversational)"],
    certificationsTraining: ["AWS Solutions Architect Associate"],
    awards: [],
  },
};
