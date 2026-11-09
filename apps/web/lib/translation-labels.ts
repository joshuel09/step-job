/** Message keys for API field identifiers; unknown fields use `other`. */
export const TRANSLATION_FIELDS: Record<string, string> = {
  job_title: "jobTitle",
  description: "description",
  qualification: "qualification",
  field_of_study: "fieldOfStudy",
  name: "name",
  title: "title",
  challenge: "challenge",
  action: "action",
  result: "result",
};

/** Every dynamic success notice must resolve in both interface catalogues. */
export const TRANSLATION_NOTICES = ["saved", "removed", "nameSaved"] as const;
export type TranslationNotice = (typeof TRANSLATION_NOTICES)[number];
