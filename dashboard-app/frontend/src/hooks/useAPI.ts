import { useCallback, useMemo } from 'react'

const BASE_URL = ''

export function useAPI() {
  const request = useCallback(async (
    method: string,
    endpoint: string,
    body?: any
  ) => {
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    }

    if (body) {
      options.body = JSON.stringify(body)
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, options)

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API error: ${response.status} - ${error}`)
    }

    return response.json()
  }, [])

  const get = useCallback((endpoint: string) => request('GET', endpoint), [request])
  const post = useCallback((endpoint: string, body?: any) => request('POST', endpoint, body), [request])
  const put = useCallback((endpoint: string, body?: any) => request('PUT', endpoint, body), [request])
  const del = useCallback((endpoint: string) => request('DELETE', endpoint), [request])

  return useMemo(() => ({ get, post, put, del }), [get, post, put, del])
}
