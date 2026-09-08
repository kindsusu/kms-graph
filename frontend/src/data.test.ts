import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { isSafeExternalUrl, parsePayload, PayloadError } from './data';

const item = { id: 'a', title: '자료', kind: 'document', subtype: '', description: '', owner: '', department: '', domain: '', tags: [] };

describe('parsePayload', () => {
  it('parses the schema v2 sample consumed by the Python builder', () => {
    const samplePath = fileURLToPath(new URL('../../sample/knowledge.json', import.meta.url));
    const payload = parsePayload(JSON.parse(readFileSync(samplePath, 'utf8')));
    expect(payload.items).toHaveLength(4);
    expect(payload.relations).toHaveLength(3);
  });
  it('accepts required metadata fields when they are empty strings', () => {
    expect(parsePayload({ schemaVersion: 2, title: 'KMS', generatedAt: '2026-01-01', items: [item], relations: [] }).items[0]).toMatchObject(item);
  });
  it('permits prompt only for prompt AI assets', () => {
    expect(() => parsePayload({ schemaVersion: 2, title: 'KMS', generatedAt: 'x', items: [{ ...item, prompt: 'secret' }], relations: [] })).toThrow(PayloadError);
    expect(parsePayload({ schemaVersion: 2, title: 'KMS', generatedAt: 'x', items: [{ ...item, kind: 'ai_asset', subtype: '프롬프트', prompt: '초안' }], relations: [] }).items[0].prompt).toBe('초안');
  });
  it('rejects self and duplicate relation tuples', () => {
    const b = { ...item, id: 'b', title: '다른 자료' };
    const base = { schemaVersion: 2, title: 'KMS', generatedAt: 'x', items: [item, b] };
    expect(() => parsePayload({ ...base, relations: [{ id: 'r', source: 'a', target: 'a', type: 'related', label: '' }] })).toThrow(/자기 자신/);
    expect(() => parsePayload({ ...base, relations: [{ id: 'r1', source: 'a', target: 'b', type: 'related', label: '' }, { id: 'r2', source: 'a', target: 'b', type: 'related', label: '' }] })).toThrow(/중복 관계/);
  });
});

describe('isSafeExternalUrl', () => {
  it('allows plain HTTP(S) addresses and rejects credentials or control whitespace', () => {
    expect(isSafeExternalUrl('https://example.com/a')).toBe(true);
    expect(isSafeExternalUrl('https://user:pass@example.com')).toBe(false);
    expect(isSafeExternalUrl('javascript:alert(1)')).toBe(false);
    expect(isSafeExternalUrl('https://example.com/\nnext')).toBe(false);
  });
});
