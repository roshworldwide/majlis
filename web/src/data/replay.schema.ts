/**
 * zod mirror of `majlis/replay.schema.json` (JSON Schema 2020-12).
 * Objects are `.passthrough()` so that the golden run may add fields without
 * breaking the renderer. The front end is a pure renderer of this contract.
 */
import { z } from 'zod';

export const EVENT_TYPES = [
  'inject',
  'message',
  'proposal',
  'gate_pass',
  'gate_block',
  'gate_flag',
  'belief',
  'gap',
  'adviser_qa',
  'kpi',
  'action',
] as const;

export const GAP_TYPES = [
  'unclear_responsibility',
  'standards_gap',
  'technology_gap',
  'legislative_gap',
  'coordination_problem',
  'conflicting_objectives',
] as const;

export const CLUSTERS = ['uae', 'global', 'itu', 'other'] as const;

const pair = z.tuple([z.number(), z.number()]);
const series = z.array(pair);

export const EventSchema = z
  .object({
    seq: z.number().int().optional(),
    t: z.number(),
    wave: z.string(),
    type: z.enum(EVENT_TYPES),
    agent: z.string().nullable(),
    payload: z.record(z.any()),
  })
  .passthrough();

export const TimelineSchema = z.array(EventSchema);

export const KpisSchema = z
  .object({
    cells_asleep_pct: series,
    call_setup_success: series,
    emergency_call_success: series.optional(),
    ambulance_delta_min: series,
  })
  .passthrough();

export const GapSchema = z
  .object({
    gap_id: z.string(),
    type: z.enum(GAP_TYPES),
    title: z.string(),
    description: z.string().optional(),
    domain: z.string().optional(),
    trigger: z.string().optional(),
    global_examples: z.array(
      z
        .object({
          label: z.string(),
          cite_id: z.string(),
          how: z.string().optional(),
        })
        .passthrough(),
    ),
    uae_evidence: z.array(z.string()).optional(),
    absence_queries: z.array(z.string()).optional(),
    readiness_ids: z.array(z.string()),
    y3172_nodes: z.array(z.string()),
    recommendation: z.string().optional(),
    confidence: z.string().optional(),
    t: z.number(),
  })
  .passthrough();

export const CitationSchema = z
  .object({
    doc_id: z.string(),
    chunk_id: z.string().optional(),
    title: z.string(),
    issuer: z.string().optional(),
    article: z.string(),
    page: z.number().int().nullable(),
    quote: z.string(),
    url: z.string(),
    verified: z.boolean(),
    cluster: z.enum(CLUSTERS).optional(),
    star_index: z.number().int().nullable().optional(),
  })
  .passthrough();

export const AuditSchema = z
  .object({
    href: z.string(),
    root: z.string(),
    entries: z.number().int().optional(),
  })
  .passthrough();

export const MetaSchema = z
  .object({
    run_id: z.string(),
    scenario: z.string(),
    title: z.string().optional(),
    reform: z.string().nullable(),
    created_at: z.string(),
    llm: z.object({ provider: z.string(), model: z.string(), mode: z.string() }).passthrough(),
    audit_root: z.string(),
    disclaimer: z.string(),
    label: z.string().optional(),
    clock_origin: z.string().optional(),
    horizon_min: z.number().optional(),
    mock: z.boolean().optional(),
    quotable: z.string().optional(),
    cells_total: z.number().optional(),
  })
  .passthrough();

export const AgentSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    name_ar: z.string(),
    role_type: z.string(),
    modelled_on: z.string(),
    color: z.string(),
    mandates: z.array(
      z
        .object({
          id: z.string(),
          title: z.string().optional(),
          action_types: z.array(z.string()),
          citations: z.array(z.string()),
        })
        .passthrough(),
    ),
  })
  .passthrough();

export const ChannelSchema = z
  .object({
    from: z.string(),
    to: z.string(),
    legal: z.boolean(),
    citation: z.string().nullable(),
    type: z.string().optional(),
    latency_min: z.number().optional(),
    origin: z.enum(['law', 'reform', 'missing']).optional(),
  })
  .passthrough();

export const FactSchema = z
  .object({ id: z.string(), label: z.string(), label_ar: z.string() })
  .passthrough();

export const WaveSchema = z
  .object({
    id: z.string(),
    t: z.number(),
    visible_to: z.array(z.string()),
    content: z.string(),
    hidden_fact: z.string().optional(),
  })
  .passthrough();

export const ReplaySchema = z
  .object({
    meta: MetaSchema,
    agents: z.array(AgentSchema),
    channels: z.array(ChannelSchema),
    facts: z.array(FactSchema),
    waves: z.array(WaveSchema),
    timeline: TimelineSchema,
    kpis: KpisSchema,
    gaps: z.array(GapSchema),
    citations: z.record(CitationSchema),
    kb_points: z
      .object({
        href: z.string(),
        count: z.number().int(),
        clusters: z.array(z.enum(CLUSTERS)),
        layout: z.string().optional(),
      })
      .passthrough(),
    audit: AuditSchema,
    compare: z
      .object({
        baseline_run: z.string(),
        reform_run: z.string().nullable(),
        metrics: z.record(z.any()),
        reform: z
          .object({
            run_id: z.string(),
            timeline: TimelineSchema,
            kpis: KpisSchema,
            gaps: z.array(GapSchema),
            audit: AuditSchema.optional(),
          })
          .passthrough()
          .optional(),
      })
      .passthrough(),
    adviser_presets: z.array(z.record(z.any())).optional(),
  })
  .passthrough();

export type Replay = z.infer<typeof ReplaySchema>;
export type ReplayEvent = z.infer<typeof EventSchema>;
export type Gap = z.infer<typeof GapSchema>;
export type Citation = z.infer<typeof CitationSchema>;
export type Agent = z.infer<typeof AgentSchema>;
export type Channel = z.infer<typeof ChannelSchema>;
export type Fact = z.infer<typeof FactSchema>;
export type Kpis = z.infer<typeof KpisSchema>;
export type GapType = (typeof GAP_TYPES)[number];
export type EventType = (typeof EVENT_TYPES)[number];
