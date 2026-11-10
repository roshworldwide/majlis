import { useStore } from '../state/store';
import type { GapType } from '../data/replay.schema';

const EN = {
  fictional: 'FICTIONAL SIMULATION',
  run: 'Run',
  story: 'Story',
  explore: 'Explore',
  present: 'Present',
  sound: 'Sound',
  verify: 'Verify chain',
  verifying: 'Verifying…',
  verified: 'entries verified',
  notVerified: 'chain NOT verified',
  root: 'root',
  pipeline: 'Y.3172 pipeline',
  council: 'The Council',
  city: 'The City',
  evidence: 'The Evidence',
  reform: 'Rewind & Reform',
  coldOpen: 'Cold open',
  illustrative: 'Illustrative city · abstract and stylised',
  cellsAsleep: 'Cells asleep',
  callSetup: 'Call setup success',
  emergency: 'Emergency-call success',
  ambulance: 'Ambulance response Δ',
  simClock: 'Sim clock',
  modelledOn: 'modelled on',
  beliefs: 'Beliefs',
  mandates: 'Mandates',
  verdicts: 'Gate verdicts',
  messages: 'Messages',
  globalExamples: 'Global examples',
  readiness: 'Readiness IDs',
  y3172: 'Y.3172 nodes',
  quoteVerified: '✓ quote verified in source',
  quoteUnverified: 'quote not verified in source',
  close: 'Close',
  replayReform: 'Replay with reform pack',
  adviser: 'Adviser console',
  presets: 'Preset questions',
  freeText: 'Free-text questions go live only when `majlis serve` is running locally.',
  finale: 'Baseline vs reform pack',
  baseline: 'Baseline',
  withReform: 'With reform',
  never: 'never',
  gapsFound: 'Gaps found',
  skip: 'Press any key to skip',
  play: 'Play',
  pause: 'Pause',
  speed: 'Speed',
  lite: '2D Experience',
  liteWhy: 'Showing the 2D Experience',
  timeToAwareness: 'Time to awareness (sim minutes)',
  knows: 'knows',
} as const;

type Dict = Record<keyof typeof EN, string>;

const AR: Dict = {
  fictional: 'محاكاة خيالية',
  run: 'التشغيل',
  story: 'القصة',
  explore: 'استكشاف',
  present: 'عرض',
  sound: 'الصوت',
  verify: 'تحقّق من السلسلة',
  verifying: 'جارٍ التحقق…',
  verified: 'إدخالات تم التحقق منها',
  notVerified: 'السلسلة غير مُتحقَّق منها',
  root: 'الجذر',
  pipeline: 'مسار Y.3172',
  council: 'المجلس',
  city: 'المدينة',
  evidence: 'الأدلة',
  reform: 'الإرجاع والإصلاح',
  coldOpen: 'الافتتاح',
  illustrative: 'مدينة توضيحية · مجردة ومنمّقة',
  cellsAsleep: 'الخلايا النائمة',
  callSetup: 'نجاح إنشاء المكالمات',
  emergency: 'نجاح مكالمات الطوارئ',
  ambulance: 'فرق زمن الإسعاف',
  simClock: 'ساعة المحاكاة',
  modelledOn: 'مستوحى من',
  beliefs: 'المعارف',
  mandates: 'الصلاحيات',
  verdicts: 'قرارات البوابة',
  messages: 'الرسائل',
  globalExamples: 'أمثلة عالمية',
  readiness: 'معرّفات الجاهزية',
  y3172: 'عُقد Y.3172',
  quoteVerified: '✓ الاقتباس مُتحقَّق منه في المصدر',
  quoteUnverified: 'الاقتباس غير مُتحقَّق منه',
  close: 'إغلاق',
  replayReform: 'إعادة التشغيل مع حزمة الإصلاح',
  adviser: 'وحدة المستشار',
  presets: 'أسئلة جاهزة',
  freeText: 'الأسئلة الحرة متاحة فقط عند تشغيل `majlis serve` محلياً.',
  finale: 'الأساس مقابل حزمة الإصلاح',
  baseline: 'الأساس',
  withReform: 'مع الإصلاح',
  never: 'أبداً',
  gapsFound: 'الفجوات المكتشفة',
  skip: 'اضغط أي مفتاح للتخطي',
  play: 'تشغيل',
  pause: 'إيقاف',
  speed: 'السرعة',
  lite: 'التجربة ثنائية الأبعاد',
  liteWhy: 'عرض التجربة ثنائية الأبعاد',
  timeToAwareness: 'زمن الإدراك (دقائق المحاكاة)',
  knows: 'يعرف',
};

export type Key = keyof typeof EN;

export function useT(): (k: Key) => string {
  const lang = useStore((s) => s.lang);
  return (k: Key) => (lang === 'ar' ? AR[k] : EN[k]);
}

export function tr(k: Key, lang: 'en' | 'ar'): string {
  return lang === 'ar' ? AR[k] : EN[k];
}

export const GAP_LABEL: Record<GapType, { en: string; ar: string }> = {
  legislative_gap: { en: 'LEGISLATIVE GAP', ar: 'فجوة تشريعية' },
  unclear_responsibility: { en: 'UNCLEAR RESPONSIBILITY', ar: 'مسؤولية غير واضحة' },
  coordination_problem: { en: 'COORDINATION PROBLEM', ar: 'مشكلة تنسيق' },
  conflicting_objectives: { en: 'CONFLICTING OBJECTIVES', ar: 'أهداف متعارضة' },
  standards_gap: { en: 'STANDARDS GAP', ar: 'فجوة معايير' },
  technology_gap: { en: 'TECHNOLOGY GAP', ar: 'فجوة تقنية' },
};

export function gapLabel(type: string, lang: 'en' | 'ar'): string {
  const g = GAP_LABEL[type as GapType];
  if (!g) return type.replace(/_/g, ' ').toUpperCase();
  return lang === 'ar' ? g.ar : g.en;
}
