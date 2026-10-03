# Feature Specification: Document the missing API settings in .env.example

**Feature Branch**: `004-env-example-vars`

**Created**: 2026-10-03

**Status**: Draft

**Issue**: #58

**Input**: User description: "Three settings exist in `apps/api/app/core/settings.py` but are missing from `.env.example`, so a fresh clone has no idea they exist. Add `AI_PROVIDER`, `OPENAI_API_KEY` and `WEB_ORIGINS`, keeping the file's existing comment style. Done when someone can copy `.env.example` to `.env`, run the API against the web app, and hit no undocumented setting."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A fresh clone runs the API against the web app (Priority: P1)

A developer clones the repository, copies `apps/api/.env.example` to `.env` without editing it, starts the API and the web app locally, and the web app talks to the API. Nothing reaches an external AI provider.

**Why this priority**: This is the setup path the ticket exists for. If the copied file leaves out the web app's address, the browser refuses every call to the API and the developer has to read the source to find out why.

**Independent Test**: In a clean checkout, copy the example file to `.env`, start the API and the web app on their default ports, and load a page that calls the API. The call succeeds and nothing goes out to an AI provider.

**Acceptance Scenarios**:

1. **Given** a fresh clone with `.env` copied unchanged from `.env.example`, **When** the developer starts the API and opens the web app at its default address, **Then** the browser's requests to the API are accepted.
2. **Given** the same unchanged copy, **When** any feature that uses AI runs, **Then** it uses the offline provider and makes no network call.

---

### User Story 2 - A developer switches to a real provider or a different web address (Priority: P2)

A developer who wants real AI output, or who serves the web app from a different address or port, finds out from the example file alone which settings to change and what values they take.

**Why this priority**: These settings are less common, but finding them should not mean reading the source.

**Independent Test**: Give the example file to someone who hasn't seen the code and ask them to point the API at a real provider and add a second web address. They can do both from the file's comments alone.

**Acceptance Scenarios**:

1. **Given** the example file, **When** a developer reads the provider setting, **Then** it lists the accepted values (`fake`, `openai`) and says the key is only read when `openai` is chosen.
2. **Given** the example file, **When** a developer reads the web address setting, **Then** it says what the setting is for, that a wrong value means the browser is refused, and how to give more than one address.

---

### Edge Cases

- `OPENAI_API_KEY` is left empty while `AI_PROVIDER=fake`: this is the default, and it works.
- More than one web address is needed (for example `localhost` and `127.0.0.1`): the example says the values are separated by commas.
- A developer pastes a real key into `.env`: the file's existing warning never to commit a filled-in `.env` still covers this. The example itself must contain no key.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `apps/api/.env.example` MUST list `AI_PROVIDER` with the default value `fake`.
- **FR-002**: `apps/api/.env.example` MUST list `OPENAI_API_KEY` with an empty value.
- **FR-003**: `apps/api/.env.example` MUST list `WEB_ORIGINS` with the default value `http://localhost:3000`.
- **FR-004**: Each of the three settings MUST have a comment above it saying what it is for, in the same style as the comments already in the file.
- **FR-005**: The provider comment MUST name the accepted values and say that `fake` keeps local work and continuous integration off the network.
- **FR-006**: The key comment MUST say that the key is only read when `AI_PROVIDER=openai`.
- **FR-007**: The web address comment MUST say that a wrong value means the browser is refused, and that more than one address can be given, separated by commas.
- **FR-008**: The values in the example MUST match the defaults in the application, so copying the file changes no behaviour.
- **FR-009**: The example MUST contain no secret values.

### Key Entities

- **API environment example** (`apps/api/.env.example`): the template a developer copies to `.env`. Each entry is a variable name, a safe default value and a comment explaining what it does.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from a fresh clone to the web app talking to the API using only the copied example file, with no edits.
- **SC-002**: All three settings named in the ticket appear in the example, and each has an explanatory comment.
- **SC-003**: Copying the example to `.env` gives the same behaviour as having no `.env` for these three settings: the same defaults.
- **SC-004**: No secret appears in the example file.

## Assumptions

- Scope is the three settings named in #58. Other settings that also have defaults in the code (`AI_MODEL`, `REDIS_URL`, `IMPORT_DEADLINE_SECONDS`, `AI_MAX_RETRIES`, `DELETION_RECOVERY_DAYS`) are left out. Their defaults work for local use, and some exist only so tests can adjust them.
- The web app runs at `http://localhost:3000` by default.
- No change to application code is needed. The settings already exist and already read from the environment.
