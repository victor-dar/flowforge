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

  it('keeps protected areas unavailable when there is no stored token', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Bem-vindo de volta' })).toBeInTheDocument()
    expect(screen.queryByText('Visão geral')).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('logs in and loads the authenticated user workspace', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes('/api/auth/login')) {
        return jsonResponse({
          access_token: 'new-session-token',
          user: { id: 2, email: 'owner@example.com' },
        })
      }
      if (String(input).includes('/api/auth/me')) {
        return jsonResponse({ id: 2, email: 'owner@example.com' })
      }
      return jsonResponse([existingBot])
    })

    render(<App />)

    await user.type(screen.getByLabelText('E-mail'), 'owner@example.com')
    await user.type(screen.getByLabelText('Senha'), 'uma-senha-segura')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findAllByText(existingBot.name)).not.toHaveLength(0)
    expect(screen.getByText('owner@example.com')).toBeInTheDocument()
    expect(localStorage.getItem('flowforge-token')).toBe('new-session-token')
  })

  it('restores the authenticated profile from the session endpoint', async () => {
    localStorage.setItem('flowforge-token', 'stored-session-token')
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes('/api/auth/me')) {
        return jsonResponse({ id: 7, email: 'restored@example.com' })
      }
      return jsonResponse([existingBot])
    })

    render(<App />)

    expect(await screen.findByText('restored@example.com')).toBeInTheDocument()
  })

  it('logs out, removes the token and clears the previous account data', async () => {
    const user = userEvent.setup()
    localStorage.setItem('flowforge-token', 'previous-session-token')
    vi.mocked(fetch).mockResolvedValue(jsonResponse([existingBot]))

    render(<App />)

    expect(await screen.findAllByText(existingBot.name)).not.toHaveLength(0)
    await user.click(screen.getByText('Sair da conta'))

    expect(localStorage.getItem('flowforge-token')).toBeNull()
    expect(screen.getByRole('heading', { name: 'Bem-vindo de volta' })).toBeInTheDocument()
    expect(screen.queryByText(existingBot.name)).not.toBeInTheDocument()
  })

  it('keeps the user authenticated when loading bots fails due to a network error', async () => {
    localStorage.setItem('flowforge-token', 'valid-session-token')
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'))

    render(<App />)

    expect(
      await screen.findByText(
        'Não foi possível carregar seus assistentes. Verifique a conexão com a API e tente novamente.',
      ),
    ).toBeInTheDocument()
    expect(localStorage.getItem('flowforge-token')).toBe('valid-session-token')
    expect(screen.getByRole('heading', { name: 'Bom trabalho. Vamos automatizar?' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Bem-vindo de volta' })).not.toBeInTheDocument()
  })
})
