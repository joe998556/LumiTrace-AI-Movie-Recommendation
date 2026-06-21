export const meta = {
  name: 'lean-cross-eval',
  description: '5 experts, 3 playlists each, cross-evaluate for quick iteration',
  phases: [
    { title: 'Generate', detail: '5 experts x 3 playlists = 15' },
    { title: 'Search', detail: '15 playlists via /search' },
    { title: 'Evaluate', detail: 'Cross-evaluation by partner experts' },
  ],
}

const SEARCH_URL = 'http://127.0.0.1:5001/search'

const EXPERTS = [
  {
    name: 'Film Noir 探偵', pairWith: 'Cyberpunk 未來觀察員',
    desc: '犯罪、懸疑、黑色電影、偵探故事的專家',
    genres: [80, 9648, 53], langs: ['en', 'zh', 'ko'],
    prompts: [
      { name: '經典黑色偵探', overviews: ['一個私家偵探在雨夜的城市裡追查一樁離奇失蹤案，發現幕後牽涉到權貴階層的陰謀'], genre_ids: [80, 9648, 53], langs: ['en', 'zh'] },
      { name: '韓國犯罪懸疑', overviews: ['韓國社會底層的連環殺人案件，警方與兇手之間的心理博弈，結局令人意想不到'], genre_ids: [80, 53, 9648], langs: ['ko'] },
      { name: '心理驚悚推理', overviews: ['一個看似普通的案件背後隱藏著驚人的真相，不可靠的敘事者讓觀眾不斷懷疑自己的判斷'], genre_ids: [53, 9648], langs: ['en', 'ja'] },
    ],
  },
  {
    name: '東亞影評人', pairWith: '獨立影展策展人',
    desc: '日本、韓國、台灣、香港電影的專家',
    genres: [18, 35, 10749], langs: ['ja', 'ko', 'zh'],
    prompts: [
      { name: '深夜食堂系溫暖', overviews: ['安靜的夜晚，一個人在城市角落裡找到溫暖的故事，帶有淡淡憂傷和人性光輝'], genre_ids: [18, 35], langs: ['ja', 'ko', 'zh'] },
      { name: '台灣新電影風格', overviews: ['慢節奏的台灣鄉村故事，家庭關係的細膩描寫，帶有侯孝賢式的長鏡頭美學'], genre_ids: [18], langs: ['zh'] },
      { name: '日本動畫大師', overviews: ['帶有奇幻色彩的日本動畫，關於成長與自然的寓言故事，視覺風格獨特'], genre_ids: [16, 14], langs: ['ja'] },
    ],
  },
  {
    name: '暗夜說書人', pairWith: '浪漫劇場導演',
    desc: '恐怖、驚悚、心理懸疑的專家',
    genres: [27, 53, 9648], langs: ['en', 'ja', 'ko'],
    prompts: [
      { name: '日式怨靈恐怖', overviews: ['日本傳統怨靈故事，陰森的氛圍營造，不靠跳嚇而是心理層面的恐懼'], genre_ids: [27, 53], langs: ['ja'] },
      { name: '邪教與偏遠村莊', overviews: ['一群人來到偏遠村莊，發現當地有詭異的邪教儀式，逐漸陷入無法逃脫的噩夢'], genre_ids: [27, 9648], langs: ['en'] },
      { name: '韓國社會驚悚', overviews: ['韓國社會階級矛盾引發的驚悚事件，貧富差距下的极端人性展現'], genre_ids: [53, 18, 80], langs: ['ko'] },
    ],
  },
  {
    name: '爆米花將軍', pairWith: '經典時光守護者',
    desc: '動作、冒險、商業大片的專家',
    genres: [28, 12, 878], langs: ['en', 'zh'],
    prompts: [
      { name: '科幻太空冒險', overviews: ['人類探索未知宇宙的壯闊旅程，面對外星文明的挑戰與自我發現'], genre_ids: [878, 12], langs: ['en'] },
      { name: '亞洲動作猛片', overviews: ['華語或韓國的硬派動作片，精緻的武打場面搭配緊湊的劇情'], genre_ids: [28, 53], langs: ['zh', 'ko'] },
      { name: '超級英雄集結', overviews: ['多位超級英雄聯手對抗强大反派，有幽默感也有史詩級的戰鬥場面'], genre_ids: [28, 878, 12], langs: ['en'] },
    ],
  },
  {
    name: '浪漫劇場導演', pairWith: '暗夜說書人',
    desc: '愛情、劇情、文藝片的專家',
    genres: [10749, 18, 35], langs: ['zh', 'en', 'fr'],
    prompts: [
      { name: '舊時代遺憾戀曲', overviews: ['戰亂年代中被迫分離的戀人，跨越數十年的等待與遺憾，內斂深沉的愛情'], genre_ids: [10749, 18, 10752], langs: ['zh', 'en'] },
      { name: '異國旅途怦然心動', overviews: ['在異國旅行中偶然相遇的兩個人，短暫而深刻的浪漫情緣'], genre_ids: [10749, 35, 12], langs: ['en', 'fr'] },
      { name: '壓抑年代禁忌之戀', overviews: ['在保守社會中不被允許的愛情，兩人必須在壓力與真愛之間做出抉擇'], genre_ids: [10749, 18], langs: ['en', 'zh'] },
    ],
  },
]

function makePlaylistPayload(p) {
  return JSON.stringify({
    overviews: p.overviews,
    playlist_genre_ids: p.genre_ids || [],
    preferred_languages: p.langs || [],
    top_k: 10,
  })
}

function buildEvalPrompt(evaluator, generatorName, playlist, results) {
  return `你是「${evaluator.name}」，${evaluator.desc}。
你的 partner「${generatorName}」產出了片單「${playlist.name}」：${playlist.overviews.join(' ')}

推薦系統回傳：
${results.map((r, i) => `${i+1}. [${r.id}] ${r.title} (${(r.release_date||'').slice(0,4)}) score=${r.score} genre=${JSON.stringify(r.genre_ids||[])}`).join('\n')}

請評分 (0-5)：
relevance: 推薦是否符合片單意圖
diversity: 年代語言類型是否多元
surprise: 有沒有意外但合理的推薦

回傳 JSON only:
{"relevance":N,"diversity":N,"surprise":N,"misses":["Movie (year)"],"garbage_ids":[id],"comment":"..."}`
}

// ── Phase 1: Generate ────────────────────────────────────────────
phase('Generate')

const playlists = await parallel(
  EXPERTS.map(exp => async () => {
    const prompt = `你是「${exp.name}」，${exp.desc}。
請為以下 3 組主題各產生一組搜尋測試：
${exp.prompts.map((p, i) => `${i+1}. ${p.name}: ${p.overviews[0]}`).join('\n')}

回傳 JSON 陣列：
[{"name":"主題名","overviews":["描述"],"playlist_genre_ids":[...],"preferred_languages":[...]}]
只回 JSON。`
    const raw = await agent(prompt, { label: `gen:${exp.name}`, phase: 'Generate' })
    try {
      let arr = JSON.parse(raw)
      if (!Array.isArray(arr)) { const m = raw.match(/\[[\s\S]*\]/); arr = m ? JSON.parse(m[0]) : [] }
      return arr.map((p, i) => ({ ...p, _expert: exp.name, _pairWith: exp.pairWith, _idx: i }))
    } catch {
      // Fallback: use the predefined prompts
      return exp.prompts.map((p, i) => ({
        name: p.name, overviews: p.overviews,
        playlist_genre_ids: p.genre_ids, preferred_languages: p.langs,
        _expert: exp.name, _pairWith: exp.pairWith, _idx: i,
      }))
    }
  })
)

const flatPlaylists = playlists.flat()
log(`Generated ${flatPlaylists.length} playlists`)

// ── Phase 2: Search ──────────────────────────────────────────────
phase('Search')

const searchResults = await parallel(
  flatPlaylists.map(pl => async () => {
    const body = makePlaylistPayload(pl)
    const pyScript = `import requests,json,sys; sys.stdout.reconfigure(encoding='utf-8'); r=requests.post('${SEARCH_URL}',json=${body}); print(json.dumps(r.json()))`
    const raw = await agent(
      `Run this Python one-liner and return ONLY its output:\npython -c "${pyScript.replace(/"/g, '\\"')}"`,
      { label: `search:${pl.name}`, phase: 'Search' }
    )
    try {
      const d = JSON.parse(raw)
      return { playlist: pl, results: d.results || [] }
    } catch {
      const m = raw.match(/\{[\s\S]*\}/)
      if (m) { try { const d = JSON.parse(m[0]); return { playlist: pl, results: d.results || [] } } catch {} }
      return { playlist: pl, results: [] }
    }
  })
)

const validSearches = searchResults.filter(r => r.results.length > 0)
log(`Searches: ${validSearches.length}/${searchResults.length}`)

// ── Phase 3: Cross-Evaluate ──────────────────────────────────────
phase('Evaluate')

const evals = await parallel(
  EXPERTS.map(exp => async () => {
    // Evaluate partner's playlists
    const partnerPlays = validSearches.filter(s => s.playlist._expert === exp.pairWith)
    const results = []
    for (const sr of partnerPlays) {
      const raw = await agent(buildEvalPrompt(exp, exp.pairWith, sr.playlist, sr.results), {
        label: `eval:${exp.name}→${sr.playlist.name}`, phase: 'Evaluate',
      })
      try {
        let score = JSON.parse(raw)
        results.push({ evaluator: exp.name, generator: exp.pairWith, playlist: sr.playlist.name, ...score })
      } catch {
        const m = raw.match(/\{[\s\S]*\}/)
        if (m) { try { results.push({ evaluator: exp.name, generator: exp.pairWith, playlist: sr.playlist.name, ...JSON.parse(m[0]) }) } catch {} }
      }
    }
    return results
  })
)

const flatEvals = evals.flat()
log(`Evaluations: ${flatEvals.length}`)

// ── Aggregate ────────────────────────────────────────────────────
const avg = (arr, key) => {
  const vals = arr.filter(e => e[key] != null).map(e => Number(e[key]))
  return vals.length ? +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : null
}

const summary = {
  playlists: flatPlaylists.length,
  searches: validSearches.length,
  evaluations: flatEvals.length,
  avg_relevance: avg(flatEvals, 'relevance'),
  avg_diversity: avg(flatEvals, 'diversity'),
  avg_surprise: avg(flatEvals, 'surprise'),
  garbage_total: flatEvals.reduce((n, e) => n + (e.garbage_ids || []).length, 0),
  by_evaluator: EXPERTS.map(exp => {
    const evs = flatEvals.filter(e => e.evaluator === exp.name)
    return {
      evaluator: exp.name,
      count: evs.length,
      avg_relevance: avg(evs, 'relevance'),
      avg_diversity: avg(evs, 'diversity'),
      avg_surprise: avg(evs, 'surprise'),
    }
  }),
  comments: flatEvals.map(e => ({ evaluator: e.evaluator, playlist: e.playlist, relevance: e.relevance, comment: e.comment })),
}

return summary
