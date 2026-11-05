'use client'

import { useState } from 'react'

import useAIChatStreamHandler from '@/hooks/useAIStreamHandler'
import { cn } from '@/lib/utils'

export interface ReplyChoice {
  label: string
  value: string
}

export interface ReplyChoiceSet {
  mode: 'single' | 'multiple'
  prompt: string
  options: ReplyChoice[]
}

const FENCE = /```assetmind-choices\s*([\s\S]*?)```/

export function splitChoices(content: string): {
  prose: string
  choices: ReplyChoiceSet | null
} {
  const match = content.match(FENCE)
  if (!match) {
    return { prose: content, choices: null }
  }
  try {
    const parsed = JSON.parse(match[1]) as {
      mode?: string
      prompt?: unknown
      options?: Array<{ label?: unknown; value?: unknown }>
    }
    if (parsed.mode !== 'single' && parsed.mode !== 'multiple') {
      return { prose: content, choices: null }
    }
    const options = (parsed.options ?? []).flatMap((option) => {
      if (typeof option.label !== 'string' || typeof option.value !== 'string') {
        return []
      }
      return [{ label: option.label, value: option.value }]
    })
    if (options.length === 0) {
      return { prose: content, choices: null }
    }
    const prompt = typeof parsed.prompt === 'string' ? parsed.prompt : ''
    const prose = content
      .replace(match[0], '')
      .replace(prompt, '')
      .trim()
    return {
      prose,
      choices: { mode: parsed.mode, prompt, options }
    }
  } catch {
    return { prose: content, choices: null }
  }
}

const ReplyChoices = ({
  choices,
  interactive
}: {
  choices: ReplyChoiceSet
  interactive: boolean
}) => {
  const { handleStreamResponse } = useAIChatStreamHandler()
  const [selected, setSelected] = useState<string[]>([])
  const multiple = choices.mode === 'multiple'

  const send = (values: string[]) => {
    if (!interactive || values.length === 0) {
      return
    }
    void handleStreamResponse(values.join(', '))
  }

  return (
    <div className="flex w-full max-w-xl flex-col gap-2">
      {choices.prompt ? (
        <p className="text-sm leading-relaxed text-secondary">{choices.prompt}</p>
      ) : null}
      {choices.options.map((option) => {
        const active = selected.includes(option.value)
        return (
          <button
            key={option.value}
            type="button"
            disabled={!interactive}
            aria-pressed={active}
            onClick={() => {
              if (!multiple) {
                send([option.value])
                return
              }
              setSelected((current) =>
                current.includes(option.value)
                  ? current.filter((value) => value !== option.value)
                  : [...current, option.value]
              )
            }}
            className={cn(
              'flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left text-sm transition-colors',
              'disabled:cursor-default disabled:opacity-70',
              active
                ? 'border-primary/70 bg-primary/10 text-primary'
                : 'border-white/15 text-secondary hover:bg-white/5'
            )}
          >
            <span
              className={cn(
                'flex h-4 w-4 shrink-0 items-center justify-center border border-white/40',
                multiple ? 'rounded-[4px]' : 'rounded-full'
              )}
            >
              {active ? (
                <span
                  className={cn(
                    'bg-primary',
                    multiple ? 'h-2 w-2 rounded-[2px]' : 'h-2 w-2 rounded-full'
                  )}
                />
              ) : null}
            </span>
            <span>{option.label}</span>
          </button>
        )
      })}
      {multiple ? (
        <button
          type="button"
          disabled={!interactive || selected.length === 0}
          onClick={() => send(selected)}
          className="mt-1 self-end rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
        >
          Continuar
        </button>
      ) : null}
    </div>
  )
}

export default ReplyChoices
