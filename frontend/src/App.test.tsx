import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

const existingBot = {
  id: 8,
  name: 'Assistente da sessão anterior',
  business_name: 'Empresa anterior',
  description: '',
  instructions: 'Seja útil.',
  welcome_message: 'Olá!',
  color: '#6d5dfc',
  allowed_domains: [],
  created_at: '2026-01-01T00:00:00',
  document_count: 0,
}

describe('FlowForge authentication session', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('keeps protected areas unavailable when there is no stored session', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: 'Autenticação necessária' }, 401))
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Bem-vindo de volta' })).toBeInTheDocument()
    expect(screen.queryByText('Visão geral')).not.toBeInTheDocument()
  })

  it('logs in and loads the authenticated user workspace', async () => {
    const user = userEvent.setup()
    let loggedIn = false
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes('/api/auth/login')) {
        loggedIn = true
        return jsonResponse({
          access_token: 'new-session-token',
          user: { id: 2, email: 'owner@example.com' },
        })
      }
      if (String(input).includes('/api/auth/me')) {
        if (!loggedIn) return jsonResponse({ detail: 'Autenticação necessária' }, 401)
        return jsonResponse({ id: 2, email: 'owner@example.com' })
      }
      return jsonResponse([existingBot])
    })

    render(<App />)

    await screen.findByRole('heading', { name: 'Bem-vindo de volta' })
    await user.type(screen.getByLabelText('E-mail'), 'owner@example.com')
    await user.type(screen.getByLabelText('Senha'), 'uma-senha-segura')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findAllByText(existingBot.name)).not.toHaveLength(0)
    expect(screen.getByText('owner@example.com')).toBeInTheDocument()
  })

  it('restores the authenticated profile from the session endpoint', async () => {
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes('/api/auth/me')) {
        return jsonResponse({ id: 7, email: 'restored@example.com' })
      }
      return jsonResponse([existingBot])
    })

    render(<App />)

    expect(await screen.findByText('restored@example.com')).toBeInTheDocument()
  })

  it('logs out and clears the previous account data', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes('/api/auth/me')) {
        return jsonResponse({ id: 7, email: 'owner@example.com' })
      }
      return jsonResponse([existingBot])
    })

    render(<App />)

    expect(await screen.findAllByText(existingBot.name)).not.toHaveLength(0)
    await user.click(screen.getByText('Sair da conta'))

    expect(screen.getByRole('heading', { name: 'Bem-vindo de volta' })).toBeInTheDocument()
    expect(screen.queryByText(existingBot.name)).not.toBeInTheDocument()
  })

  it('lists and deletes documents in the knowledge base', async () => {
    const user = userEvent.setup()
    let documentDeleted = false
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.includes('/api/auth/me')) {
        return jsonResponse({ id: 7, email: 'owner@example.com' })
      }
      if (url.includes('/documents/1') && init?.method === 'DELETE') {
        documentDeleted = true
        return jsonResponse(null, 204)
      }
      if (url.includes('/documents')) {
        if (documentDeleted) return jsonResponse([])
        return jsonResponse([
          {
            id: 1,
            name: 'manual.txt',
            size_chars: 120,
            created_at: '2026-11-20T12:00:00',
          },
        ])
      }
      return jsonResponse([{ ...existingBot, document_count: 1 }])
    })

    render(<App />)

    await user.click((await screen.findAllByText(existingBot.name))[0])
    await user.click(screen.getByRole('button', { name: /Base de conhecimento/i }))
    expect(await screen.findByText('manual.txt')).toBeInTheDocument()
    expect(screen.getByText(/120 caracteres/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Excluir documento manual.txt' }))
    await waitFor(() => {
      expect(screen.queryByText('manual.txt')).not.toBeInTheDocument()
    })
  })

  it('keeps the user authenticated when loading bots fails due to a network error', async () => {
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes('/api/auth/me')) {
        return jsonResponse({ id: 7, email: 'owner@example.com' })
      }
      throw new TypeError('Failed to fetch')
    })

    render(<App />)

    expect(
      await screen.findByText(
        'Não foi possível carregar seus assistentes. Verifique a conexão com a API e tente novamente.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Bom trabalho. Vamos automatizar?' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Bem-vindo de volta' })).not.toBeInTheDocument()
  })
})
