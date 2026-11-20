import { FormEvent, useEffect, useState } from 'react'
import './style.css'
import './p0.css'

type Bot = {
  id: number
  name: string
  business_name: string
  description: string
  instructions: string
  welcome_message: string
  color: string
  allowed_domains: string[]
  document_count: number
}

type Message = { role: string; content: string }
type DocumentItem = {
  id: number
  name: string
  size_chars: number
  created_at: string
}

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function errorMessage(error: unknown) {
  if (error instanceof TypeError) {
    return 'Não foi possível conectar à API. Verifique se o servidor está ativo e tente novamente.'
  }
  return error instanceof Error ? error.message : 'Ocorreu um erro inesperado.'
}

function responseError(data: { detail?: unknown }, fallback: string) {
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : ''))
      .filter(Boolean)
      .join(' ')
  }
  return fallback
}

async function request(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...init.headers,
    },
  })

  if (!response.ok) {
    const result = await response.json().catch(() => ({}))
    throw new ApiError(
      responseError(result, 'Não foi possível concluir a operação.'),
      response.status,
    )
  }

  return response.status === 204 ? null : response.json()
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(false)
  const [sessionChecked, setSessionChecked] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [register, setRegister] = useState(false)
  const [bots, setBots] = useState<Bot[]>([])
  const [selected, setSelected] = useState<Bot | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [conversation, setConversation] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState('overview')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newBotName, setNewBotName] = useState('')
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  const loadDocuments = async (botId: number) => {
    setDocumentsLoading(true)
    try {
      setDocuments(await request(`/api/bots/${botId}/documents`))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setDocumentsLoading(false)
    }
  }

  const refresh = async () => {
    setLoading(true)
    try {
      const data = await request('/api/bots')
      setBots(data)
      if (selected) {
        setSelected(data.find((bot: Bot) => bot.id === selected.id) || null)
      }
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    void fetch(`${API}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => undefined)
    setAuthenticated(false)
    setSessionChecked(true)
    setEmail('')
    setPassword('')
    setBots([])
    setSelected(null)
    setMessages([])
    setConversation(null)
    setError('')
  }

  useEffect(() => {
    request('/api/auth/me')
      .then((user: { email: string }) => {
        setEmail(user.email)
        setAuthenticated(true)
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) setAuthenticated(false)
        else setError('Não foi possível verificar sua sessão.')
      })
      .finally(() => setSessionChecked(true))
  }, [])

  useEffect(() => {
    if (authenticated) {
      refresh().catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) logout()
        else setError('Não foi possível carregar seus assistentes. Verifique a conexão com a API e tente novamente.')
      })
    }
  }, [authenticated])

  useEffect(() => {
    if (selected && tab === 'knowledge') {
      void loadDocuments(selected.id)
    }
  }, [selected?.id, tab])

  const auth = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')

    try {
      const data = await fetch(`${API}/api/auth/${register ? 'register' : 'login'}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const result = await data.json().catch(() => ({}))

      if (!data.ok) {
        throw new ApiError(responseError(result, 'Falha ao entrar.'), data.status)
      }

      setEmail(result.user.email)
      setAuthenticated(true)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const openBot = (bot: Bot) => {
    setSelected(bot)
    setTab('overview')
    setMessages([])
    setConversation(null)
    setDocuments([])
    void loadDocuments(bot.id)
  }

  const createBot = async () => {
    const name = newBotName.trim()
    if (!name) return

    try {
      const bot = await request('/api/bots', {
        method: 'POST',
        body: JSON.stringify({ name, business_name: '', description: '' }),
      })

      setBots((current) => [bot, ...current])
      setIsCreateOpen(false)
      setNewBotName('')
      openBot(bot)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  const update = async (changes: Partial<Bot>) => {
    if (!selected) return

    setSaveState('saving')

    try {
      const updated = await request(`/api/bots/${selected.id}`, {
        method: 'PATCH',
        body: JSON.stringify(changes),
      })

      setSelected(updated)
      setBots((current) => current.map((bot) => (bot.id === updated.id ? updated : bot)))
      setSaveState('saved')
      window.setTimeout(() => setSaveState('idle'), 1400)
    } catch (e) {
      setError(errorMessage(e))
      setSaveState('idle')
    }
  }

  const remove = async (bot: Bot) => {
    if (!window.confirm(`Excluir “${bot.name}” e todos os seus dados?`)) return

    try {
      await request(`/api/bots/${bot.id}`, { method: 'DELETE' })
      setBots((current) => current.filter((item) => item.id !== bot.id))
      if (selected?.id === bot.id) setSelected(null)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  const send = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected || !question.trim()) return

    const text = question.trim()
    setQuestion('')
    setMessages((current) => [...current, { role: 'user', content: text }])
    setBusy(true)

    try {
      const response = await fetch(`${API}/api/public/bots/${selected.id}/chat`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, visitor_id: 'dashboard-test', conversation_id: conversation }),
      })
      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || 'Falha ao responder')
      }

      if (!result.answer) {
        throw new Error('Falha ao responder')
      }

      setConversation(result.conversation_id)
      setMessages((current) => [...current, { role: 'assistant', content: result.answer }])
    } catch (e) {
      setMessages((current) => [...current, { role: 'assistant', content: errorMessage(e) }])
    } finally {
      setBusy(false)
    }
  }

  const upload = async (file?: File) => {
    if (!file || !selected) return

    const allowedExtensions = ['pdf', 'txt', 'md', 'csv']
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (!extension || !allowedExtensions.includes(extension)) {
      setError('Formato não suportado. Envie PDF, TXT, MD ou CSV.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('O arquivo excede o limite de 5 MB.')
      return
    }

    const form = new FormData()
    form.append('file', file)
    setUploading(true)

    try {
      await request(`/api/bots/${selected.id}/documents`, { method: 'POST', body: form })
      await refresh()
      await loadDocuments(selected.id)
      setError('')
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setUploading(false)
    }
  }

  const removeDocument = async (document: DocumentItem) => {
    if (!selected || !window.confirm(`Excluir o documento “${document.name}”?`)) return

    try {
      await request(`/api/bots/${selected.id}/documents/${document.id}`, { method: 'DELETE' })
      await refresh()
      await loadDocuments(selected.id)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  const totalDocuments = bots.reduce((sum, bot) => sum + bot.document_count, 0)

  if (!sessionChecked) {
    return (
      <main className="auth-page">
        <p className="muted">Verificando sua sessão…</p>
      </main>
    )
  }

  if (!authenticated) {
    return (
      <main className="auth-page">
        <div className="auth-card">
          <div className="brand">
            <span className="brand-icon">✳</span>
            <span>FlowForge</span>
          </div>

          <p className="eyebrow">SUA IDEIA. SUA INTELIGÊNCIA.</p>
          <h1>{register ? 'Crie sua conta' : 'Bem-vindo de volta'}</h1>
          <p className="muted">Crie assistentes inteligentes para o seu negócio — sem escrever código.</p>

          <form onSubmit={auth}>
            <label>
              E-mail
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="voce@empresa.com" />
            </label>

            <label>
              Senha
              <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Mínimo de 8 caracteres" />
            </label>

            {error && <p className="error">{error}</p>}

            <button className="primary full" disabled={busy}>
              {busy ? 'Aguarde…' : register ? 'Criar conta' : 'Entrar'}
            </button>
          </form>

          <p className="switch">
            {register ? 'Já tem uma conta?' : 'Ainda não tem uma conta?'}
            <button type="button" onClick={() => { setRegister(!register); setError('') }}>
              {register ? 'Entrar' : 'Cadastre-se'}
            </button>
          </p>
        </div>
      </main>
    )
  }

  return (
    <div className="layout">
      {isCreateOpen && (
        <div className="modal-backdrop" onClick={() => setIsCreateOpen(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <p className="eyebrow">NOVO ASSISTENTE</p>
                <h3>Crie seu chatbot</h3>
              </div>
              <button className="icon-button" type="button" onClick={() => setIsCreateOpen(false)} aria-label="Fechar">×</button>
            </div>

            <label>
              Nome do assistente
              <input
                value={newBotName}
                onChange={(e) => setNewBotName(e.target.value)}
                placeholder="Ex.: Vendedora de salão"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    createBot()
                  }
                }}
              />
            </label>

            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setIsCreateOpen(false)}>
                Cancelar
              </button>
              <button className="primary" type="button" disabled={!newBotName.trim()} onClick={createBot}>
                Criar assistente
              </button>
            </div>
          </div>
        </div>
      )}

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">✳</span>
          <span>FlowForge</span>
        </div>

        <div className="workspace">
          <div className="workspace-icon">F</div>
          <div>
            <strong>Meu espaço</strong>
            <small>Plano gratuito</small>
          </div>
          <span className="chevron">⌄</span>
        </div>

        <p className="nav-label">ESPAÇO DE TRABALHO</p>
        <button className={!selected ? 'nav-item active' : 'nav-item'} onClick={() => setSelected(null)}>
          ▦ <span>Visão geral</span>
        </button>

        <div className="bot-heading">
          <p className="nav-label">SEUS ASSISTENTES</p>
          <button aria-label="Criar assistente" onClick={() => setIsCreateOpen(true)}>＋</button>
        </div>

        {bots.map((bot) => (
          <button
            key={bot.id}
            className={selected?.id === bot.id ? 'nav-item active' : 'nav-item'}
            onClick={() => openBot(bot)}
          >
            <span className="bot-dot" style={{ background: bot.color }} />
            {bot.name}
          </button>
        ))}

        <button className="nav-item create-link" onClick={() => setIsCreateOpen(true)}>
          ＋ <span>Criar assistente</span>
        </button>

        <div className="sidebar-bottom">
          <div className="usage">
            <div className="usage-row">
              <span>Mensagens este mês</span>
              <strong>—</strong>
            </div>
            <div className="progress"><i /></div>
            <small>Os limites serão habilitados em breve.</small>
          </div>

          <button
            className="profile"
            onClick={logout}
          >
            <span className="avatar">{email?.[0]?.toUpperCase() || 'U'}</span>
            <span>
              <strong>{email || 'Sua conta'}</strong>
              <small>Sair da conta</small>
            </span>
            <span className="chevron">↗</span>
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <span className="crumb">Workspace</span>
            <span className="crumb-sep">/</span>
            <strong>{selected?.name || 'Visão geral'}</strong>
          </div>
          <span className="status"><i /> Todos os sistemas operacionais</span>
        </header>

        {error && (
          <div className="toast" onClick={() => setError('')}>
            {error}
            <button type="button">×</button>
          </div>
        )}

        {!selected ? (
          <section className="content">
            <div className="welcome">
              <div>
                <p className="eyebrow">SEU NEGÓCIO MERECE MAIS TEMPO</p>
                <h1>Bom trabalho. Vamos automatizar?</h1>
                <p className="muted">Seus assistentes cuidam das perguntas repetitivas para você focar no que importa.</p>
              </div>
              <button className="primary" onClick={() => setIsCreateOpen(true)}>＋ Criar assistente</button>
            </div>

            <div className="stats">
              <article>
                <span className="stat-icon purple">✳</span>
                <p>Assistentes ativos</p>
                <strong>{bots.length}</strong>
                <small>Seu espaço de trabalho</small>
              </article>
              <article>
                <span className="stat-icon blue">◷</span>
                <p>Conversas</p>
                <strong>—</strong>
                <small>Histórico disponível por assistente</small>
              </article>
              <article>
                <span className="stat-icon green">↗</span>
                <p>Documentos</p>
                <strong>{totalDocuments}</strong>
                <small>Na sua base de conhecimento</small>
              </article>
            </div>

            {bots.length ? (
              <div className="section-title">
                <div>
                  <h2>Seus assistentes</h2>
                  <p className="muted">Gerencie e teste seus chatbots.</p>
                </div>
                <button className="secondary" onClick={() => setIsCreateOpen(true)}>＋ Novo assistente</button>
              </div>
            ) : (
              <div className="empty">
                <div className="empty-icon">✳</div>
                <h2>Seu primeiro assistente começa aqui</h2>
                <p>Conte o que seu negócio faz, adicione informações importantes e teste seu assistente em minutos.</p>
                <button className="primary" onClick={() => setIsCreateOpen(true)}>Criar meu primeiro assistente</button>
              </div>
            )}

            <div className="bot-grid">
              {bots.map((bot) => (
                <article className="bot-card" key={bot.id} onClick={() => openBot(bot)}>
                  <div className="bot-card-icon" style={{ background: `${bot.color}18`, color: bot.color }}>✳</div>
                  <button
                    className="more"
                    aria-label="Excluir"
                    onClick={(event) => {
                      event.stopPropagation()
                      remove(bot)
                    }}
                  >
                    •••
                  </button>
                  <h3>{bot.name}</h3>
                  <p>{bot.business_name || bot.description || 'Adicione informações sobre seu negócio'}</p>
                  <div className="card-footer">
                    <span>▤ {bot.document_count} documentos</span>
                    <span className="open-arrow">↗</span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : (
          <section className="content bot-content">
            <div className="bot-title">
              <div className="bot-card-icon large" style={{ background: `${selected.color}18`, color: selected.color }}>✳</div>
              <div>
                <div className="eyebrow">ASSISTENTE</div>
                <h1>{selected.name}</h1>
                <p className="muted">Configure, ensine e teste seu chatbot.</p>
              </div>

              <div className="inline-actions">
                <div className={`save-pill ${saveState !== 'idle' ? saveState : ''}`}>
                  {saveState === 'saving' ? 'Salvando…' : saveState === 'saved' ? 'Salvo' : 'Pronto'}
                </div>
                <button className="danger" onClick={() => remove(selected)}>Excluir</button>
              </div>
            </div>

            <nav className="tabs">
              <button className={tab === 'overview' ? 'tab active-tab' : 'tab'} onClick={() => setTab('overview')}>Configuração</button>
              <button className={tab === 'knowledge' ? 'tab active-tab' : 'tab'} onClick={() => setTab('knowledge')}>Base de conhecimento <span className="count">{selected.document_count}</span></button>
              <button className={tab === 'test' ? 'tab active-tab' : 'tab'} onClick={() => setTab('test')}>Testar assistente</button>
              <button className={tab === 'publish' ? 'tab active-tab' : 'tab'} onClick={() => setTab('publish')}>Publicar</button>
            </nav>

            {tab === 'overview' && (
              <div className="columns">
                <div className="panel">
                  <h2>Sobre seu negócio</h2>
                  <p className="muted">Essas informações ajudam a identificar seu assistente.</p>

                  <label>
                    Nome do assistente
                    <input
                      value={selected.name}
                      onChange={(e) => setSelected({ ...selected, name: e.target.value })}
                      onBlur={(e) => update({ name: e.target.value })}
                    />
                  </label>

                  <label>
                    Nome da empresa
                    <input
                      value={selected.business_name}
                      placeholder="Ex.: Café da Praça"
                      onChange={(e) => setSelected({ ...selected, business_name: e.target.value })}
                      onBlur={(e) => update({ business_name: e.target.value })}
                    />
                  </label>

                  <label>
                    Descrição
                    <textarea
                      value={selected.description}
                      placeholder="O que sua empresa faz?"
                      onChange={(e) => setSelected({ ...selected, description: e.target.value })}
                      onBlur={(e) => update({ description: e.target.value })}
                    />
                  </label>

                  <label>
                    Como o assistente deve responder?
                    <textarea
                      value={selected.instructions}
                      onChange={(e) => setSelected({ ...selected, instructions: e.target.value })}
                      onBlur={(e) => update({ instructions: e.target.value })}
                    />
                  </label>

                  <label>
                    Mensagem de boas-vindas
                    <input
                      value={selected.welcome_message}
                      onChange={(e) => setSelected({ ...selected, welcome_message: e.target.value })}
                      onBlur={(e) => update({ welcome_message: e.target.value })}
                    />
                  </label>

                  <label>
                    Cor principal
                    <div className="color-input">
                      <input
                        type="color"
                        value={selected.color}
                        onChange={(e) => {
                          const value = e.target.value
                          setSelected({ ...selected, color: value })
                          update({ color: value })
                        }}
                      />
                      <span>{selected.color}</span>
                    </div>
                  </label>

                  <label>
                    Domínios autorizados do widget
                    <input
                      value={(selected.allowed_domains || []).join(', ')}
                      placeholder="https://meusite.com, https://loja.meusite.com"
                      onBlur={(e) => update({
                        allowed_domains: e.target.value
                          .split(',')
                          .map((domain) => domain.trim())
                          .filter(Boolean),
                      })}
                      onChange={(e) => setSelected({
                        ...selected,
                        allowed_domains: e.target.value
                          .split(',')
                          .map((domain) => domain.trim())
                          .filter(Boolean),
                      })}
                    />
                  </label>
                </div>

                <div className="panel tip-panel">
                  <span className="stat-icon purple">✦</span>
                  <h3>Um bom assistente começa com boas informações</h3>
                  <p>Descreva seus serviços, horários, políticas e dúvidas frequentes. Depois, envie documentos na base de conhecimento.</p>
                  <button className="secondary" onClick={() => setTab('knowledge')}>Adicionar informações →</button>
                </div>
              </div>
            )}

            {tab === 'knowledge' && (
              <div className="panel knowledge-panel">
                <h2>Ensine seu assistente</h2>
                <p className="muted">Adicione documentos para que o chatbot responda com informações do seu negócio. PDF, TXT, MD e CSV (máx. 5 MB).</p>

                <label className="upload-zone" aria-busy={uploading}>
                  <span className="upload-icon">↑</span>
                  <strong>{uploading ? 'Enviando documento…' : 'Arraste arquivos ou clique para selecionar'}</strong>
                  <small>PDF, TXT, MD ou CSV • até 5 MB</small>
                  <input
                    type="file"
                    accept=".pdf,.txt,.md,.csv,application/pdf"
                    disabled={uploading}
                    onChange={(e) => upload(e.target.files?.[0])}
                  />
                </label>

                <div className="doc-list">
                  <div className="doc-row">
                    <span>▤</span>
                    <strong>Documentos carregados</strong>
                    <span>{documentsLoading ? 'Carregando…' : documents.length}</span>
                  </div>
                  {!documentsLoading && documents.length === 0 && (
                    <p className="muted">Nenhum documento enviado. Adicione arquivos para ensinar o assistente.</p>
                  )}
                  {documents.map((document) => (
                    <div className="document-row" key={document.id}>
                      <span className="document-icon">▤</span>
                      <div>
                        <strong>{document.name}</strong>
                        <small>
                          {document.size_chars.toLocaleString('pt-BR')} caracteres
                          {document.created_at ? ` • ${new Date(document.created_at).toLocaleDateString('pt-BR')}` : ''}
                        </small>
                      </div>
                      <button
                        type="button"
                        className="danger document-delete"
                        onClick={() => removeDocument(document)}
                        aria-label={`Excluir documento ${document.name}`}
                      >
                        Excluir
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tab === 'test' && (
              <div className="panel test-panel">
                <div className="test-heading">
                  <div>
                    <h2>Teste seu assistente</h2>
                    <p className="muted">Converse com ele antes de publicar.</p>
                  </div>
                  <button className="secondary" onClick={() => { setMessages([]); setConversation(null) }}>Limpar conversa</button>
                </div>

                <div className="chat-window">
                  {messages.length === 0 && (
                    <div className="chat-welcome">
                      <span style={{ color: selected.color }}>✳</span>
                      <h3>{selected.name}</h3>
                      <p>{selected.welcome_message}</p>
                    </div>
                  )}

                  {messages.map((message, index) => (
                    <div key={`${message.role}-${index}`} className={`message ${message.role}`}>
                      {message.content}
                    </div>
                  ))}

                  {busy && <div className="message assistant">Pensando…</div>}
                </div>

                <form className="chat-form" onSubmit={send}>
                  <input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Escreva uma mensagem…"
                    maxLength={4000}
                  />
                  <button className="primary" disabled={busy || !question.trim()}>
                    Enviar ↑
                  </button>
                </form>
              </div>
            )}

            {tab === 'publish' && (
              <div className="panel publish-panel">
                <span className="stat-icon green">↗</span>
                <h2>Publique em seu site</h2>
                <p className="muted">
                  Adicione este trecho antes do fechamento da tag <code>&lt;/body&gt;</code>. O widget do FlowForge estará disponível para seus visitantes.
                </p>
                <pre>{`<script src="${API}/widget.js" data-bot-id="${selected.id}" defer></script>`}</pre>
                <p className="muted">O widget pode ser testado após iniciar a API. Configure a URL pública da API em VITE_API_URL.</p>

                <div className="publish-checklist">
                  <h3>Checklist de publicação</h3>
                  {[
                    { label: 'Nome do assistente configurado', done: selected.name.trim().length > 0 },
                    { label: 'Mensagem de boas-vindas configurada', done: selected.welcome_message.trim().length > 0 },
                    { label: 'Instruções adicionadas', done: selected.instructions.trim().length > 0 },
                    { label: 'Base de conhecimento com documentos', done: documents.length > 0 },
                    { label: 'Domínios do widget configurados', done: (selected.allowed_domains || []).length > 0 },
                  ].map((item) => (
                    <div className={`checklist-item ${item.done ? 'done' : ''}`} key={item.label}>
                      <span aria-hidden="true">{item.done ? '✓' : '○'}</span>
                      <strong>{item.label}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}
