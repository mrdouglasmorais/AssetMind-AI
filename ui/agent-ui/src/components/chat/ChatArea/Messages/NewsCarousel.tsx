'use client'

import { useRef, useState } from 'react'

import { cn } from '@/lib/utils'

export interface NewsCard {
  title: string
  publisher: string
  publishedAt: string | null
  url: string
  imageUrl: string | null
}

export interface NewsSet {
  source: string
  symbol: string
  items: NewsCard[]
}

const FENCE = /```assetmind-news\s*([\s\S]*?)```/
const OPEN_FENCE = /```assetmind-news[\s\S]*?(```|$)/
const LOOSE_JSON = /\{\s*"symbol"\s*:[\s\S]*$/

export function splitNews(content: string): { prose: string; news: NewsSet | null } {
  const match = content.match(FENCE)
  if (!match) {
    return { prose: content, news: null }
  }
  try {
    const parsed = JSON.parse(match[1]) as {
      source?: unknown
      symbol?: unknown
      items?: Array<{
        title?: unknown
        publisher?: unknown
        published_at?: unknown
        url?: unknown
        image_url?: unknown
      }>
    }
    const items = (parsed.items ?? []).flatMap((item) => {
      if (typeof item.title !== 'string' || typeof item.url !== 'string') {
        return []
      }
      if (!item.url.startsWith('https://')) {
        return []
      }
      const imageUrl =
        typeof item.image_url === 'string' && item.image_url.startsWith('https://')
          ? item.image_url
          : null
      return [
        {
          title: item.title,
          publisher: typeof item.publisher === 'string' ? item.publisher : '',
          publishedAt: typeof item.published_at === 'string' ? item.published_at : null,
          url: item.url,
          imageUrl
        }
      ]
    })
    if (items.length === 0) {
      return { prose: content, news: null }
    }
    return {
      prose: content.replace(match[0], '').trim(),
      news: {
        source: typeof parsed.source === 'string' ? parsed.source : '',
        symbol: typeof parsed.symbol === 'string' ? parsed.symbol : '',
        items
      }
    }
  } catch {
    return { prose: content, news: null }
  }
}

export function newsFromTools(
  tools: Array<{ tool_name?: string; content?: string | null; result?: string | null }> | undefined
): NewsSet | null {
  for (const tool of tools ?? []) {
    const payload = tool.content || tool.result
    if (!payload || (tool.tool_name && tool.tool_name !== 'get_asset_news')) {
      continue
    }
    const parsed = splitNews(payload)
    if (parsed.news) {
      return parsed.news
    }
  }
  return null
}

export function hideNewsJson(content: string): string {
  return content.replace(OPEN_FENCE, '').replace(LOOSE_JSON, '').replace(/\n{3,}/g, '\n\n').trim()
}

function formatDate(value: string | null): string {
  if (!value) {
    return ''
  }
  const day = value.slice(0, 10)
  const [year, month, date] = day.split('-')
  if (!year || !month || !date) {
    return ''
  }
  return `${date}/${month}/${year}`
}

const PALETTES = [
  ['#1d4e4a', '#c4a574'],
  ['#243056', '#d08a5a'],
  ['#3d2a45', '#7ea18a']
]

const Illustration = ({ index }: { index: number }) => {
  const [ink, accent] = PALETTES[index % PALETTES.length]
  return (
    <svg viewBox="0 0 320 180" className="h-full w-full" role="img" aria-label="Ilustração">
      <rect width="320" height="180" fill={ink} />
      <circle cx="250" cy="36" r="48" fill={accent} opacity="0.85" />
      <rect x="24" y="108" width="120" height="8" rx="4" fill="white" opacity="0.55" />
      <rect x="24" y="126" width="78" height="8" rx="4" fill="white" opacity="0.3" />
      <path d="M24 78 C70 78 78 28 130 40 C170 48 176 92 230 70" fill="none" stroke={accent} strokeWidth="6" />
    </svg>
  )
}

const CardImage = ({ item, index }: { item: NewsCard; index: number }) => {
  const [failed, setFailed] = useState(false)
  if (!item.imageUrl || failed) {
    return <Illustration index={index} />
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={item.imageUrl}
      alt=""
      className="h-full w-full object-cover"
      onError={() => setFailed(true)}
    />
  )
}

const NewsCarousel = ({ news }: { news: NewsSet }) => {
  const scroller = useRef<HTMLDivElement>(null)

  const scrollByCard = (direction: number) => {
    scroller.current?.scrollBy({ left: direction * 288, behavior: 'smooth' })
  }

  return (
    <div className="w-full max-w-xl">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs uppercase tracking-wide text-secondary">
          {news.symbol ? `${news.symbol} · ` : ''}
          {news.source || 'Manchetes'}
        </p>
        <div className="flex gap-1">
          <button
            type="button"
            aria-label="Manchete anterior"
            onClick={() => scrollByCard(-1)}
            className="rounded-full border border-white/15 px-2 py-1 text-xs text-secondary hover:bg-white/5"
          >
            ‹
          </button>
          <button
            type="button"
            aria-label="Próxima manchete"
            onClick={() => scrollByCard(1)}
            className="rounded-full border border-white/15 px-2 py-1 text-xs text-secondary hover:bg-white/5"
          >
            ›
          </button>
        </div>
      </div>
      <div
        ref={scroller}
        className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {news.items.map((item, index) => {
          const when = formatDate(item.publishedAt)
          return (
            <a
              key={item.url}
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className={cn(
                'w-64 shrink-0 snap-start overflow-hidden rounded-2xl border border-white/15',
                'bg-white/5 text-secondary transition-colors hover:border-primary/50'
              )}
            >
              <div className="h-36 w-full overflow-hidden">
                <CardImage item={item} index={index} />
              </div>
              <div className="flex h-32 flex-col justify-between p-3">
                <p className="line-clamp-3 text-sm leading-snug text-primary">{item.title}</p>
                <p className="truncate text-xs text-secondary">
                  {[item.publisher, when].filter(Boolean).join(' · ')}
                </p>
              </div>
            </a>
          )
        })}
      </div>
    </div>
  )
}

export default NewsCarousel
