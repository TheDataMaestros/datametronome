import { describe, expect, it, vi } from 'vitest'

vi.mock('~/services/api', () => ({ apiService: {} }))

const { parseS3Tables } = await import('~/services/staves')

/**
 * S3 staves declare their tables as free text, and the parsed result is
 * interpolated into CREATE VIEW server-side. Both the shape and the rejections
 * matter.
 */
describe('parseS3Tables', () => {
  it('reads one table per line', () => {
    expect(parseS3Tables('users = users/*.parquet')).toEqual({
      tables: { users: 'users/*.parquet' },
    })
  })

  it('keeps = inside a partition glob', () => {
    // Splitting on every = would turn orders/dt=*/*.parquet into nonsense.
    expect(parseS3Tables('orders = orders/dt=*/*.parquet')).toEqual({
      tables: { orders: 'orders/dt=*/*.parquet' },
    })
  })

  it('reads several lines and ignores blanks and comments', () => {
    const input = [
      '# analytics exports',
      'users = users/*.parquet',
      '',
      '  orders = orders/*.parquet  ',
    ].join('\n')

    expect(parseS3Tables(input)).toEqual({
      tables: { users: 'users/*.parquet', orders: 'orders/*.parquet' },
    })
  })

  it('names the line that has no =', () => {
    const result = parseS3Tables('users = a.parquet\nbroken line')
    expect(result).toEqual({ error: expect.stringContaining('Line 2') })
  })

  it('rejects a missing path', () => {
    expect(parseS3Tables('users =')).toEqual({
      error: expect.stringContaining('no path'),
    })
  })

  it('rejects a missing name', () => {
    expect(parseS3Tables('= users/*.parquet')).toEqual({
      error: expect.stringContaining('no table name'),
    })
  })

  it('rejects a name that is not an identifier', () => {
    // The server rejects these too; catching it here explains why.
    const result = parseS3Tables('my table = x.parquet')
    expect(result).toEqual({ error: expect.stringContaining('must be letters') })
  })

  it('rejects a name that could close the CREATE VIEW quote', () => {
    const result = parseS3Tables('x" AS SELECT 1; -- = x.parquet')
    expect('error' in result).toBe(true)
  })

  it('rejects a duplicate name', () => {
    const result = parseS3Tables('users = a.parquet\nusers = b.parquet')
    expect(result).toEqual({ error: expect.stringContaining('twice') })
  })

  it('rejects an empty list', () => {
    expect(parseS3Tables('')).toEqual({
      error: expect.stringContaining('at least one table'),
    })
    expect(parseS3Tables('   \n # only a comment')).toEqual({
      error: expect.stringContaining('at least one table'),
    })
  })
})
