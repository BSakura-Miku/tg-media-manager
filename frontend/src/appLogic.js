export const DEFAULT_MEDIA_FILTERS = Object.freeze({
  q: '',
  media_type: 'all',
  tag: '',
  author: '',
  face_group: '',
  favorite: '',
  has_subtitles: '',
  min_duration: '',
  max_duration: '',
  resolution: '',
  semantic: '',
});

export const DEFAULT_PAGE = 'quickFind';
export const STALE_JOB_AFTER_MS = 10 * 60 * 1000;

const QUICK_FIND_TAG_TERMS = ['室内', '户外', '制服', '水手服', '露脸', '自拍', 'COS', 'JK', '黑丝', '白丝'];

export function parsePageHash(hash, validPages, fallback = DEFAULT_PAGE) {
  const pages = validPages instanceof Set ? validPages : new Set(validPages || []);
  const page = String(hash || '')
    .replace(/^#\/?/, '')
    .split(/[/?]/, 1)[0];
  return pages.has(page) ? page : fallback;
}

export function pageHash(page) {
  return `#${page}`;
}

export function parseJobTime(value) {
  if (!value) return null;
  const raw = String(value).trim().replace('T', ' ').replace(/\.\d+$/, '');
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return null;
  const [, year, month, day, hour, minute, second = '00'] = match;
  return Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second));
}

function jobTextBlob(job) {
  return [job?.message, job?.stdout, job?.stderr].filter(Boolean).join('\n').toLowerCase();
}

export function isInterruptedJob(job) {
  return job?.status === 'interrupted'
    || (job?.status === 'failed' && jobTextBlob(job).includes('interrupted by service restart'));
}

export function isCancelledJob(job) {
  return job?.status === 'cancelled' || jobTextBlob(job).includes('cancel');
}

export function isStaleJob(job, now = Date.now(), staleAfterMs = STALE_JOB_AFTER_MS) {
  if (!['queued', 'running'].includes(job?.status)) return false;
  const stamp = parseJobTime(job.heartbeat_at || job.started_at || job.created_at);
  if (!stamp) return false;
  return now - stamp > staleAfterMs;
}

export function jobKind(job, now = Date.now()) {
  if (job?.status === 'done') return 'completed';
  if (['warning', 'interrupted'].includes(job?.status)) return 'warning';
  if (['queued', 'running'].includes(job?.status)) return isStaleJob(job, now) ? 'warning' : 'running';
  if (isCancelledJob(job) || isInterruptedJob(job)) return 'warning';
  if (job?.status === 'failed') return 'error';
  return 'warning';
}

export function jobNeedsAttention(job, now = Date.now()) {
  return jobKind(job, now) !== 'completed';
}

export function buildQuickFindPreset(value, baseFilters = DEFAULT_MEDIA_FILTERS) {
  const text = String(value || '').trim();
  const next = {
    ...DEFAULT_MEDIA_FILTERS,
    ...(baseFilters || {}),
    q: text,
    semantic: baseFilters?.semantic || 'true',
  };
  const durationMatch = text.match(/(\d+)\s*(?:分钟|min).*?(以上|大于|超过|\+)/);
  if (durationMatch) next.min_duration = String(Number(durationMatch[1]) * 60);
  if (/4k|2160/i.test(text)) next.resolution = '4K';
  if (/1080/.test(text)) next.resolution = '1080';
  const tagTerms = QUICK_FIND_TAG_TERMS.filter(term => text.includes(term));
  if (tagTerms.length) next.tag = tagTerms.join(',');
  return next;
}

export function buildFreshQuickFindPreset(value) {
  return buildQuickFindPreset(value, DEFAULT_MEDIA_FILTERS);
}

export function addRecentSearch(current, value, limit = 8) {
  const text = String(value || '').trim();
  const existing = Array.isArray(current) ? current : [];
  if (!text) return existing;
  return [text, ...existing.filter(item => item !== text)].slice(0, limit);
}

export function appendUniqueMediaItems(existingItems, incomingItems) {
  const existing = Array.isArray(existingItems) ? existingItems : [];
  const incoming = Array.isArray(incomingItems) ? incomingItems : [];
  const seen = new Set(existing.map(item => item?.id));
  const added = incoming.filter(item => !seen.has(item?.id));
  return {
    items: [...existing, ...added],
    addedCount: added.length,
  };
}

export function pageWindow(offset, total, pageSize = 48) {
  const size = Math.max(1, Math.floor(Number(pageSize) || 1));
  const count = Math.max(0, Math.floor(Number(total) || 0));
  const pageCount = Math.max(1, Math.ceil(count / size));
  const requested = Math.max(0, Math.floor(Number(offset) || 0));
  const safeOffset = Math.min(Math.floor(requested / size) * size, (pageCount - 1) * size);
  const page = Math.floor(safeOffset / size) + 1;
  return {
    offset: safeOffset,
    page,
    pageCount,
    start: count ? safeOffset + 1 : 0,
    end: Math.min(count, safeOffset + size),
    hasPrevious: safeOffset > 0,
    hasNext: safeOffset + size < count,
    previousOffset: Math.max(0, safeOffset - size),
    nextOffset: safeOffset + size,
  };
}

export function formatFaceDistance(value) {
  if (value === null || value === undefined || value === '') return '–';
  const distance = Number(value);
  if (!Number.isFinite(distance)) return '–';
  if (distance < 0.001) return '< 0.001';
  return distance.toFixed(3);
}
