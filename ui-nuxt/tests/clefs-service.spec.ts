import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.fn()
const put = vi.fn()
const get = vi.fn()

vi.mock('~/services/api', () => ({
  apiService: {
    post: (...args: unknown[]) => post(...args),
    put: (...args: unknown[]) => put(...args),
    get: (...args: unknown[]) => get(...args),
  },
}))

const { clefsService } = await import('~/services/clefs')

/**
 * These cover the two contract mismatches that made clef creation impossible.
 *
 * Both were invisible to lint, to the build, and to TypeScript, because the
 * declared response type described a shape the API does not send. The only
 * thing that catches this class of bug is asserting against what the server
 * actually returns.
 */
describe('clefsService write payloads', () => {
  beforeEach(() => {
    post.mockReset().mockResolvedValue({ data: {} })
    put.mockReset().mockResolvedValue({ data: {} })
    get.mockReset()
  })

  const base = {
    name: 'users table has rows',
    stave_id: 'stave-1',
    check_type: 'row_count',
    configuration: { table: 'users', expected_min: 1 },
  }

  it('sends config, not configuration', async () => {
    // The API field is `config`. Posting `configuration` returned 422 for
    // every create, and the UI swallowed it.
    await clefsService.create(base)

    const [, body] = post.mock.calls[0]
    expect(body.config).toEqual({ table: 'users', expected_min: 1 })
    expect(body).not.toHaveProperty('configuration')
  })

  it('omits an empty schedule rather than sending ""', async () => {
    // The server's cron validator rejects "", it does not read it as
    // "no schedule".
    await clefsService.create({ ...base, schedule: '' })

    const [, body] = post.mock.calls[0]
    expect(body).not.toHaveProperty('schedule')
  })

  it('keeps a real schedule', async () => {
    await clefsService.create({ ...base, schedule: '0 * * * *' })

    const [, body] = post.mock.calls[0]
    expect(body.schedule).toBe('0 * * * *')
  })

  it('maps the same way on update', async () => {
    await clefsService.update('clef-1', { configuration: { table: 'orders' } })

    const [, body] = put.mock.calls[0]
    expect(body.config).toEqual({ table: 'orders' })
    expect(body).not.toHaveProperty('configuration')
  })
})

describe('clefsService read shapes', () => {
  beforeEach(() => {
    get.mockReset()
  })

  it('exposes the API config as configuration', async () => {
    get.mockResolvedValue({
      data: [{ id: 'c1', name: 'x', config: { table: 'users' } }],
    })

    const clefs = await clefsService.getAll()
    expect(clefs[0].configuration).toEqual({ table: 'users' })
  })

  it('reads check types by name and display_name', async () => {
    // Pinned to what GET /clefs/types actually returns. The UI previously read
    // ct.type, which does not exist, so every template got type: undefined and
    // selecting one silently did nothing.
    get.mockResolvedValue({
      data: {
        check_types: [
          {
            name: 'row_count',
            display_name: 'Row Count',
            description: 'Validates expected row counts',
            tier: 1,
          },
        ],
        by_tier: { '1': [], '2': [], '3': [], '4': [] },
      },
    })

    const { check_types: types } = await clefsService.getAvailableTypes()
    expect(types[0].name).toBe('row_count')
    expect(types[0].display_name).toBe('Row Count')
    expect(types[0]).not.toHaveProperty('type')
  })
})
