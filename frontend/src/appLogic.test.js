import { describe, expect, it } from 'vitest';
import {
  DEFAULT_MEDIA_FILTERS,
  addRecentSearch,
  appendUniqueMediaItems,
  buildFreshQuickFindPreset,
  buildQuickFindPreset,
  formatFaceDistance,
  isStaleJob,
  jobKind,
  jobNeedsAttention,
  pageWindow,
  pageHash,
  parsePageHash,
} from './appLogic.js';

describe('hash routing', () => {
  const pages = new Set(['dashboard', 'quickFind', 'settings']);

  it('accepts both compact and slash-prefixed hashes', () => {
    expect(parsePageHash('#dashboard', pages)).toBe('dashboard');
    expect(parsePageHash('#/settings', pages)).toBe('settings');
    expect(pageHash('quickFind')).toBe('#quickFind');
  });

  it('falls back safely for empty or unknown hashes', () => {
    expect(parsePageHash('', pages)).toBe('quickFind');
    expect(parsePageHash('#missing', pages)).toBe('quickFind');
    expect(parsePageHash('#missing', pages, 'dashboard')).toBe('dashboard');
  });
});

describe('job status and attention classification', () => {
  const now = Date.UTC(2026, 6, 23, 12, 30, 0);

  it('separates completed, active, stale, failed, cancelled, and interrupted jobs', () => {
    expect(jobKind({ status: 'done' }, now)).toBe('completed');
    expect(jobKind({ status: 'running', heartbeat_at: '2026-07-23 12:25:00' }, now)).toBe('running');
    expect(jobKind({ status: 'running', heartbeat_at: '2026-07-23 12:00:00' }, now)).toBe('warning');
    expect(jobKind({ status: 'failed', stderr: 'model crashed' }, now)).toBe('error');
    expect(jobKind({ status: 'failed', message: 'cancel requested by user' }, now)).toBe('warning');
    expect(jobKind({ status: 'failed', stderr: 'Interrupted by service restart' }, now)).toBe('warning');
  });

  it('marks every non-completed job for the attention view', () => {
    expect(jobNeedsAttention({ status: 'done' }, now)).toBe(false);
    expect(jobNeedsAttention({ status: 'running', heartbeat_at: '2026-07-23 12:25:00' }, now)).toBe(true);
    expect(jobNeedsAttention({ status: 'failed' }, now)).toBe(true);
    expect(isStaleJob({ status: 'queued', created_at: '2026-07-23 12:00:00' }, now)).toBe(true);
  });
});

describe('quick find presets and recent searches', () => {
  it('creates a fresh preset request instead of carrying stale filters', () => {
    const stale = {
      ...DEFAULT_MEDIA_FILTERS,
      q: 'old',
      tag: '旧标签',
      min_duration: '999',
      resolution: '1080',
    };
    const next = buildFreshQuickFindPreset('找 10 分钟以上 室内 制服 露脸的视频');

    expect(next).toMatchObject({
      q: '找 10 分钟以上 室内 制服 露脸的视频',
      min_duration: '600',
      resolution: '',
      tag: '室内,制服,露脸',
      semantic: 'true',
    });
    expect(stale).toMatchObject({ q: 'old', tag: '旧标签', min_duration: '999', resolution: '1080' });
  });

  it('preserves explicit filters while editing the free-form query', () => {
    const next = buildQuickFindPreset('4K COS 图片', {
      ...DEFAULT_MEDIA_FILTERS,
      media_type: 'photo',
      favorite: 'true',
    });
    expect(next).toMatchObject({
      q: '4K COS 图片',
      media_type: 'photo',
      favorite: 'true',
      resolution: '4K',
      tag: 'COS',
    });
  });

  it('deduplicates and caps recent searches from the current state', () => {
    expect(addRecentSearch(['旧', '重复', '更旧'], '重复')).toEqual(['重复', '旧', '更旧']);
    expect(addRecentSearch(['1', '2', '3'], '4', 3)).toEqual(['4', '1', '2']);
    expect(addRecentSearch(['1'], '   ')).toEqual(['1']);
  });
});

describe('media pagination', () => {
  it('counts appended media synchronously while preserving unique items', () => {
    const result = appendUniqueMediaItems(
      [{ id: 1, filename: 'one.jpg' }, { id: 2, filename: 'two.jpg' }],
      [{ id: 2, filename: 'two-new.jpg' }, { id: 3, filename: 'three.jpg' }],
    );

    expect(result.addedCount).toBe(1);
    expect(result.items.map(item => item.id)).toEqual([1, 2, 3]);
  });

  it('keeps a fixed-size page window within the result bounds', () => {
    expect(pageWindow(0, 14061, 48)).toMatchObject({
      page: 1,
      pageCount: 293,
      start: 1,
      end: 48,
      hasPrevious: false,
      hasNext: true,
      nextOffset: 48,
    });
    expect(pageWindow(99999, 100, 36)).toMatchObject({
      offset: 72,
      page: 3,
      pageCount: 3,
      start: 73,
      end: 100,
      hasPrevious: true,
      hasNext: false,
    });
    expect(pageWindow(0, 0, 48)).toMatchObject({ page: 1, pageCount: 1, start: 0, end: 0 });
  });
});

describe('face distance formatting', () => {
  it('keeps tiny distances readable without rounding them to zero', () => {
    expect(formatFaceDistance(0.0002)).toBe('< 0.001');
    expect(formatFaceDistance(0.1236)).toBe('0.124');
    expect(formatFaceDistance(null)).toBe('–');
    expect(formatFaceDistance('not-a-number')).toBe('–');
  });
});
