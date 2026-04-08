export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type GitMetadata = {
  repository: string;
  branch?: string;
  commit_sha?: string;
  issue_labels?: string[];
  files_touched?: string[];
  deployment_target?: string;
  [key: string]: JsonValue | undefined;
};

export type ProjectMetadata = {
  project: string;
  team?: string;
  cost_center?: string;
  owner?: string;
  [key: string]: JsonValue | undefined;
};

export type ArtifactRef = {
  artifact_id: string;
  kind: string;
  uri: string;
  source_system: string;
  sensitivity: string;
  timestamp: string;
  title?: string;
  digest?: string;
  preview?: string;
  attributes?: Record<string, JsonValue>;
};

export type TokenTax = {
  name: string;
  jurisdiction: string;
  rate: number;
  taxable_tokens?: number | null;
  amount?: number | null;
  currency?: string | null;
  included_in_direct_cost?: boolean;
};

export type ObservationSpanEvent = {
  event_type: "observation_span";
  source_kind: string;
  trace_id: string;
  span_id: string;
  parent_span_id?: string | null;
  span_kind: string;
  name: string;
  start_time: string;
  end_time: string;
  model_name?: string | null;
  provider?: string | null;
  tool_name?: string | null;
  token_input?: number;
  token_output?: number;
  token_taxes?: TokenTax[];
  direct_cost?: number;
  status?: string;
  attributes?: Record<string, JsonValue>;
  facets?: Record<string, JsonValue>;
  occurred_at?: string;
};

export type WorkledgerEvent = {
  event_type: string;
  source_kind: string;
  payload?: Record<string, unknown>;
  occurred_at?: string;
};

export function buildGitMetadata(input: GitMetadata): GitMetadata {
  return input;
}

export function buildProjectMetadata(input: ProjectMetadata): ProjectMetadata {
  return input;
}

export function buildArtifactRef(input: ArtifactRef): ArtifactRef {
  return input;
}

export function buildObservationSpanEvent(input: ObservationSpanEvent): ObservationSpanEvent {
  return {
    status: "ok",
    token_input: 0,
    token_output: 0,
    token_taxes: [],
    direct_cost: 0,
    attributes: {},
    facets: {},
    ...input,
  };
}

export function toJsonLines(events: Array<WorkledgerEvent | ObservationSpanEvent>): string {
  return events.map((event) => JSON.stringify(event)).join("\n");
}

export function emitObservationSpan(event: ObservationSpanEvent): string {
  return JSON.stringify({
    occurred_at: event.occurred_at ?? new Date().toISOString(),
    ...buildObservationSpanEvent(event),
  });
}

export function emitEvent(event: WorkledgerEvent): string {
  return JSON.stringify({
    occurred_at: event.occurred_at ?? new Date().toISOString(),
    ...event,
  });
}
