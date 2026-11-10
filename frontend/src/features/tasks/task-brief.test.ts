import { describe, expect, it } from 'vitest'
import { formatEstimatedCompensation, isTaskBrief, normalizeTaskBrief, parseEstimatedCompensation, parseTaskDocumentUrl, validTaskDocumentUrl } from './task-brief'

describe('optional Task documents are URLs, never fetched', () => {
  it.each(['https://drive.google.com/file/d/synthetic/view', 'http://example.test/raw', 'https://docs.google.com/document/d/synthetic/edit'])('accepts a valid HTTP(S) link %s', (url) => {
    expect(validTaskDocumentUrl(url)).toBe(true)
    expect(parseTaskDocumentUrl(` ${url} `)).toBe(url)
  })
  it.each(['javascript:alert(1)', 'data:text/plain,x', 'ftp://example.test/a', '//example.test/a', 'not a URL', 'https://example.test/with space', `https://example.test/${'a'.repeat(2048)}`])('rejects an unsafe/malformed/oversize URL %#', (url) => {
    expect(validTaskDocumentUrl(url)).toBe(false)
    expect(() => parseTaskDocumentUrl(url)).toThrow(TypeError)
  })
  it('normalizes empty input and missing old metadata to null', () => {
    expect(parseTaskDocumentUrl('  ')).toBeNull()
    expect(normalizeTaskBrief({})).toEqual({ raw_video_url: null, reference_video_url: null, template_project_url: null, script_url: null, estimated_compensation_vnd: null })
  })
})

describe('exact integer VNĐ without floating point', () => {
  it.each([['', null], ['0', '0'], ['500.000', '500000'], ['9007199254740993', '9007199254740993'], ['999.999.999.999.999.999', '999999999999999999']] as const)('parses %s exactly', (input, expected) => {
    expect(parseEstimatedCompensation(input)).toBe(expected)
  })
  it.each(['-1', '1.5', '1,5', '1e6', '+1', 'NaN', 'Infinity', '1.000.50', '1000000000000000000'])('rejects negative/fractional/exponent/overflow value %s', (input) => {
    expect(() => parseEstimatedCompensation(input)).toThrow(TypeError)
  })
  it('formats large canonical digits without loss and includes zero', () => {
    expect(formatEstimatedCompensation('9007199254740993')).toBe('9.007.199.254.740.993')
    expect(formatEstimatedCompensation('0')).toBe('0')
    expect(formatEstimatedCompensation(null)).toBe('')
  })
  it('fails closed on untrusted response metadata', () => {
    expect(isTaskBrief({ raw_video_url: 'javascript:alert(1)' })).toBe(false)
    expect(isTaskBrief({ estimated_compensation_vnd: 500000 })).toBe(false)
    expect(isTaskBrief({ estimated_compensation_vnd: '1.0' })).toBe(false)
    expect(isTaskBrief({ estimated_compensation_vnd: '9007199254740993' })).toBe(true)
  })
})
