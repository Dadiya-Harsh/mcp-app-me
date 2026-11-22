// What get_profile returns as structuredContent (content.json v1 names, camelCase).
// Keep in step with portfolio_mcp/tools/profile.py.

export type Link = { label: string; url: string };

export type ProfileData = {
  name: string;
  title: string;
  location: string;
  experienceYears: number;
  openToRoles: boolean;
  openToRolesLabel: string;
  headline: string;
  summary: string;
  tagline: string;
  focus: { title: string; description: string; href?: string | null }[];
  stats: { value: string; label: string }[];
  nowBuilding: { show: boolean; name: string; description: string; repoUrl: string } | null;
  links: {
    github: string;
    linkedin: string;
    medium: string;
    resume: string;
    resumePdf: string;
    resumeDocx: string;
    contact: string;
    booking?: string | null;
  };
  photo: string;
};
