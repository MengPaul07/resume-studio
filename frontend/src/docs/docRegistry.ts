export type DocCategory = "start" | "features" | "development" | "reference";

export type DocEntry = {
  slug: string;
  sourcePath: string;
  title: string;
  description: string;
  category: DocCategory;
  order: number;
  content: string;
};

type Frontmatter = Record<string, string>;

// Only the curated public set is bundled. Private evaluation notes and local
// operational docs stay in the repository-level docs/ directory.
const markdownModules = import.meta.glob("./content/**/*.md", {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

export const docCategoryLabels: Record<DocCategory, string> = {
  start: "开始使用",
  features: "产品功能",
  development: "开发指南",
  reference: "工程参考",
};

const pathMetadata: Record<string, Partial<Pick<DocEntry, "category" | "order" | "description">>> = {
  index: {
    category: "start",
    order: 1,
    description: "先认识 Resume Studio 的工作流，再选择适合你的入口。",
  },
  "development/setup": {
    category: "start",
    order: 2,
    description: "在本地启动前端、FastAPI 后端和可选的 JD 检索。",
  },
  "development/architecture": {
    category: "development",
    order: 10,
    description: "从浏览器状态到 Agent Loop、SSE 和存储边界，建立系统心智模型。",
  },
  "features/dashboard": {
    category: "features",
    order: 20,
    description: "管理导入文件、最近简历和四条主要工作流。",
  },
  "features/ai-tailor": {
    category: "features",
    order: 21,
    description: "用可追踪、可撤销的对话式 Agent 优化简历。",
  },
  "features/resume-builder": {
    category: "features",
    order: 22,
    description: "用实时预览、分页和 CSS 变量调整简历版式。",
  },
  "features/mock-interview": {
    category: "features",
    order: 23,
    description: "从面试设置到复盘报告，完整走一遍模拟面试。",
  },
  "features/settings": {
    category: "features",
    order: 24,
    description: "配置 LiteLLM 提供商、模型和连接测试。",
  },
};

function readFrontmatter(source: string) {
  const match = source.match(/^---\s*\n([\s\S]*?)\n---\s*\n?/);
  if (!match) return { attributes: {} as Frontmatter, content: source };

  const attributes: Frontmatter = {};
  match[1].split("\n").forEach((line) => {
    const separator = line.indexOf(":");
    if (separator === -1) return;
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, "");
    if (key && value) attributes[key] = value;
  });

  return { attributes, content: source.slice(match[0].length) };
}

function normalizePath(path: string) {
  return path.split("\\").join("/").replace(/^.*\/content\//, "").replace(/\.md$/i, "");
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9\s/-]/g, "")
    .replace(/\/+/g, "/")
    .replace(/-+/g, "-")
    .replace(/\/{2,}/g, "/");
}

function titleFromContent(content: string, fallback: string) {
  const heading = content.match(/^#\s+(.+)$/m)?.[1]?.trim();
  return heading?.replace(/[`*_]/g, "") || fallback;
}

function descriptionFromContent(content: string) {
  const paragraph = content
    .replace(/^#\s+.+$/m, "")
    .split(/\n\s*\n/)
    .map((part) => part.replace(/[`*_>#-]/g, "").replace(/\s+/g, " ").trim())
    .find((part) => part.length > 20);
  return paragraph?.slice(0, 136) || "Resume Studio 的产品、开发与工程文档。";
}

function categoryFromPath(path: string): DocCategory {
  if (path === "index" || path.endsWith("/setup")) return "start";
  if (path.startsWith("features/")) return "features";
  if (path.startsWith("development/")) return "development";
  return "reference";
}

export const docs: DocEntry[] = Object.entries(markdownModules)
  .map(([sourcePath, rawSource]) => {
    const path = normalizePath(sourcePath);
    const slug = slugify(path);
    const { attributes, content } = readFrontmatter(rawSource);
    const metadata = pathMetadata[slug] ?? {};
    const order = Number(attributes.order ?? metadata.order ?? 100);
    const category = (attributes.category as DocCategory | undefined) ?? metadata.category ?? categoryFromPath(slug);

    return {
      slug,
      sourcePath,
      title: attributes.title ?? titleFromContent(content, slug.split("/").slice(-1)[0]?.replace(/[-_]+/g, " ") ?? "Document"),
      description: attributes.description ?? metadata.description ?? descriptionFromContent(content),
      category,
      order: Number.isFinite(order) ? order : 100,
      content,
    } satisfies DocEntry;
  })
  .sort((left, right) => left.order - right.order || left.title.localeCompare(right.title, "zh-CN"));

export function findDoc(slug?: string) {
  return docs.find((doc) => doc.slug === slug?.replace(/^\/+|\/+$/g, ""));
}

export function docsByCategory(category: DocCategory) {
  return docs.filter((doc) => doc.category === category);
}
