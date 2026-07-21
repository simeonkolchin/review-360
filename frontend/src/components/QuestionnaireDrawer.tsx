import { useEffect, useState } from 'react'
import {
  Plus, Trash2, GripVertical, RotateCcw, Save, Loader2, Layers, Info,
} from 'lucide-react'
import { api, type Questionnaire, type Question } from '../api/client'
import Drawer from './Drawer'

type Draft = Question & { key: string }

const SOURCE_LABEL: Record<string, string> = {
  team: 'свой опросник команды',
  chat: 'общий опросник чата',
  default: 'набор по умолчанию',
}

let seq = 0
const draftOf = (q: Question): Draft => ({ ...q, key: `q${++seq}` })

/**
 * Questionnaire editor for one scope.
 *
 * `scope` decides where it saves: the chat template every team inherits, or one
 * team's own override. A team panel opened before anyone edited it shows the
 * inherited questions — saving is what makes them the team's own.
 */
export default function QuestionnaireDrawer({
  open, onClose, scope, id, title, onSaved,
}: {
  open: boolean
  onClose: () => void
  scope: 'chat' | 'team'
  id: number | string
  title: string
  onSaved?: () => void
}) {
  const base = scope === 'chat' ? `/chats/${id}/questionnaire` : `/teams/${id}/questionnaire`

  const [items, setItems] = useState<Draft[]>([])
  const [source, setSource] = useState<string>('default')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<null | 'save' | 'reset' | 'apply'>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [dragging, setDragging] = useState<number | null>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true); setError(null); setNote(null)
    api.get<Questionnaire>(base)
      .then(data => { setItems(data.competencies.map(draftOf)); setSource(data.source) })
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [open, base])

  const update = (key: string, patch: Partial<Draft>) =>
    setItems(list => list.map(item => (item.key === key ? { ...item, ...patch } : item)))

  const remove = (key: string) => setItems(list => list.filter(item => item.key !== key))

  const add = () =>
    setItems(list => [...list, draftOf({ id: null, name: '', description: '' })])

  const move = (from: number, to: number) =>
    setItems(list => {
      if (to < 0 || to >= list.length) return list
      const next = [...list]
      next.splice(to, 0, next.splice(from, 1)[0])
      return next
    })

  const save = async () => {
    setError(null); setBusy('save')
    try {
      const payload = {
        competencies: items.map(({ id: qid, name, description }) => ({
          // Inherited questions belong to another scope — drop their ids so the
          // server creates copies here instead of editing what everyone shares.
          id: source === scope ? qid : null,
          name: name.trim(),
          description: (description || '').trim() || null,
        })),
      }
      const saved = await api.put<Questionnaire>(base, payload)
      setItems(saved.competencies.map(draftOf))
      setSource(saved.source)
      setNote('Сохранено')
      onSaved?.()
    } catch (e) { setError((e as Error).message) } finally { setBusy(null) }
  }

  const resetToChat = async () => {
    setError(null); setBusy('reset')
    try {
      const back = await api.del<Questionnaire>(base)
      setItems(back.competencies.map(draftOf))
      setSource(back.source)
      setNote('Команда снова использует общий опросник')
      onSaved?.()
    } catch (e) { setError((e as Error).message) } finally { setBusy(null) }
  }

  const applyToTeams = async () => {
    setError(null); setBusy('apply')
    try {
      const result = await api.post<{ teams_reset: number; teams_total: number }>(
        `/chats/${id}/questionnaire/apply`,
      )
      setNote(
        result.teams_reset === 0
          ? 'Все команды и так на общем опроснике'
          : `Обновлено команд: ${result.teams_reset} из ${result.teams_total}`,
      )
      onSaved?.()
    } catch (e) { setError((e as Error).message) } finally { setBusy(null) }
  }

  const valid = items.length > 0 && items.every(i => i.name.trim())

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={title}
      subtitle={`${items.length} вопрос(ов) · сейчас действует ${SOURCE_LABEL[source] ?? source}`}
      footer={
        <>
          {scope === 'team' && source === 'team' && (
            <button className="btn btn-ghost px-3 py-2.5" onClick={resetToChat} disabled={!!busy}
                    title="Вернуться к общему опроснику чата">
              {busy === 'reset' ? <Loader2 className="w-4 h-4 spin" /> : <RotateCcw className="w-4 h-4" />}
              Как в чате
            </button>
          )}
          {scope === 'chat' && (
            <button className="btn btn-ghost px-3 py-2.5" onClick={applyToTeams} disabled={!!busy}
                    title="Сбросить индивидуальные опросники всех команд">
              {busy === 'apply' ? <Loader2 className="w-4 h-4 spin" /> : <Layers className="w-4 h-4" />}
              Обновить у всех команд
            </button>
          )}
          <div className="flex-1" />
          <button className="btn btn-primary px-5 py-2.5" onClick={save} disabled={!valid || !!busy}>
            {busy === 'save' ? <Loader2 className="w-4 h-4 spin" /> : <Save className="w-4 h-4" />}
            Сохранить
          </button>
        </>
      }>

      {scope === 'team' && source !== 'team' && (
        <div className="flex gap-2.5 items-start text-[13px] text-[var(--color-text-secondary)]
                        rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3.5 mb-4">
          <Info className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-accent)]" />
          <span>
            Команда наследует общий опросник чата. Сохраните изменения — и он станет
            индивидуальным только для неё, не затронув остальные команды.
          </span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col gap-2.5">
          {[0, 1, 2].map(i => <div key={i} className="h-[86px] rounded-xl skeleton" />)}
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {items.map((item, index) => (
            <div key={item.key}
              draggable
              onDragStart={() => setDragging(index)}
              onDragEnd={() => setDragging(null)}
              onDragOver={e => {
                e.preventDefault()
                if (dragging !== null && dragging !== index) { move(dragging, index); setDragging(index) }
              }}
              className={`rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)]
                          p-3 ${dragging === index ? 'dragging' : ''}`}>
              <div className="flex items-center gap-2">
                <span className="draggable text-[var(--color-muted)] shrink-0" title="Перетащите, чтобы поменять порядок">
                  <GripVertical className="w-4 h-4" />
                </span>
                <span className="grid place-items-center shrink-0 w-6 h-6 rounded-lg text-[11px] font-mono
                                 text-[var(--color-accent)] bg-[var(--color-surface)]
                                 border border-[var(--color-border)]">{index + 1}</span>
                <input className="input !py-2" placeholder="Компетенция, например «Коммуникация»"
                       value={item.name} onChange={e => update(item.key, { name: e.target.value })} />
                <button onClick={() => remove(item.key)} title="Удалить вопрос"
                        className="p-2 rounded-lg text-[var(--color-muted)] hover:text-[var(--color-danger)] transition shrink-0">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <input className="input !py-2 mt-2 text-[13px]"
                     placeholder="Пояснение — что именно оценивать"
                     value={item.description || ''}
                     onChange={e => update(item.key, { description: e.target.value })} />
            </div>
          ))}

          <button className="btn btn-ghost px-4 py-3 justify-center" onClick={add}
                  disabled={items.length >= 20}>
            <Plus className="w-4 h-4" /> Добавить вопрос
          </button>

          <p className="text-[12px] text-[var(--color-muted)] mt-1 mb-0">
            От 1 до 20 вопросов. Каждый оценивается по шкале 1–5. Изменения не затрагивают
            уже идущие и закрытые раунды — они держат свою копию опросника.
          </p>
        </div>
      )}

      {error && <p className="text-[var(--color-danger)] text-[13px] mt-4 mb-0">{error}</p>}
      {note && !error && <p className="text-[var(--color-success)] text-[13px] mt-4 mb-0">{note}</p>}
    </Drawer>
  )
}
