/** Isolated HTTP fixture for server-rendered and browser translation flow tests. */
import { createServer } from "node:http";

const profiles = new Map();
const failRefresh = new Set();
const role = "11111111-1111-4111-8111-111111111111";
const skill = "22222222-2222-4222-8222-222222222222";
const sourceRole = {
  entry_type: "work_experience",
  entry_id: role,
  field: "job_title",
  label: "株式会社サンプル",
  source_text: "課長",
};
const sourceSkill = {
  entry_type: "skill",
  entry_id: skill,
  field: "name",
  label: "新しい名称",
  source_text: "新しい名称",
};

/** Each browser owner gets an independent persistent fixture profile. */
function state(owner) {
  if (!profiles.has(owner))
    profiles.set(owner, {
      can_generate: true,
      missing_required: [],
      needs_english: [structuredClone(sourceRole)],
      untranslated_names: [
        {
          entry_type: "work_experience",
          entry_id: role,
          field: "employer_name",
          recorded_name: "株式会社サンプル",
        },
      ],
      stale_translations: [
        {
          id: "stale-1",
          entry_type: "skill",
          entry_id: skill,
          field: "name",
          text: "Old skill",
          approved_at: "2026-11-01T00:00:00Z",
          is_stale: true,
          source_text: "新しい名称",
        },
      ],
    });
  return profiles.get(owner);
}

const server = createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "http://localhost:3189");
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader("Access-Control-Allow-Headers", "Authorization, Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS");
  const respond = (status, value) => {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(value === undefined ? undefined : JSON.stringify(value));
  };
  if (req.method === "OPTIONS") return respond(204);
  if (req.url === "/health") return respond(200, { status: "ok" });
  const owner = req.headers.authorization?.replace(/^Bearer /, "");
  if (!owner) return respond(401, { code: "unauthorised" });
  if (owner.endsWith("000503")) return respond(503, { code: "unavailable" });
  if (owner.endsWith("000404")) return respond(404, { code: "not_found" });
  let body = "";
  for await (const chunk of req) body += chunk;
  const data = body ? JSON.parse(body) : {};
  const report = state(owner);
  if (req.method === "GET" && req.url === "/api/v1/profile/documents/resume/readiness") {
    if (failRefresh.has(owner)) return respond(503, { code: "unavailable" });
    if (owner.endsWith("000499"))
      return respond(200, {
        ...report,
        untranslated_names: report.untranslated_names.map((entry) => ({
          ...entry,
          field: "future_name",
        })),
      });
    return respond(200, report);
  }
  if (req.method === "POST" && req.url === "/api/v1/profile/translations/drafts")
    return respond(200, {
      ...data,
      source_text: data.entry_id === role ? "課長" : "新しい名称",
      text: data.entry_id === role ? "Manager" : "New skill",
      alternatives:
        data.entry_id === role
          ? [
              {
                phrase: "課長",
                options: ["Manager", "Section Chief", "Department Head"],
                note: "Choose the responsibility that matches your role.",
              },
            ]
          : [],
    });
  if (req.method === "PUT" && req.url === "/api/v1/profile/translations") {
    if (!data.text?.trim()) return respond(422, { failures: [{ field: "text", reason: "blank" }] });
    if (owner.endsWith("000504")) failRefresh.add(owner);
    report.needs_english = report.needs_english.filter(
      (item) => !(item.entry_id === data.entry_id && item.field === data.field),
    );
    report.stale_translations = report.stale_translations.filter(
      (item) => !(item.entry_id === data.entry_id && item.field === data.field),
    );
    return respond(200, {
      ...data,
      id: "approved-1",
      approved_at: new Date().toISOString(),
      is_stale: false,
    });
  }
  if (req.method === "DELETE" && req.url === "/api/v1/profile/translations/stale-1") {
    report.stale_translations = [];
    report.needs_english.push(structuredClone(sourceSkill));
    return respond(204);
  }
  if (req.method === "PATCH" && req.url === `/api/v1/profile/experiences/${role}`) {
    if (typeof data.employer_name_english !== "string" || !data.employer_name_english.trim())
      return respond(422, { failures: [] });
    report.untranslated_names = [];
    return respond(200, { id: role, ...data });
  }
  return respond(404, { code: "not_found" });
});
server.listen(8199, "127.0.0.1");
