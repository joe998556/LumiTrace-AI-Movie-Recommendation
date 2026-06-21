export const meta = {
  name: 'multi-expert-cross-eval',
  description: '20 movie expert agents (10 pairs) generate playlists, query /search, cross-evaluate each other',
  phases: [
    { title: 'Generate', detail: '20 experts generate 5 playlists each (100 total)' },
    { title: 'Search', detail: 'Feed all playlists into /search API' },
    { title: 'Cross-Evaluate', detail: 'Each expert reviews their pair-mate\'s results' },
    { title: 'Report', detail: 'Aggregate scores and produce final analysis' },
  ],
}

const SEARCH_URL = 'http://127.0.0.1:5001/search'

// ── 10 Expert Pairs ──────────────────────────────────────────────
const PAIRS = [
  {
    id: 'noir_vs_cyber',
    a: {
      name: 'Film Noir 探偵',
      desc: '犯罪、懸疑、黑色電影、偵探故事的專家。偏好陰暗氛圍、道德灰色地帶、意外反轉。',
      genres: [80, 9648, 53],
      langs: ['en', 'zh', 'ko'],
    },
    b: {
      name: 'Cyberpunk 未來觀察員',
      desc: '科幻、賽博龐克、反烏托邦、人工智慧敘事的專家。偏好未來感、科技倫理、社會批判。',
      genres: [878, 28, 53],
      langs: ['en', 'ja'],
    },
  },
  {
    id: 'asia_vs_indie',
    a: {
      name: '東亞影評人',
      desc: '日本、韓國、台灣、香港電影的專家。偏好細膩情感、社會寫實、導演風格。',
      genres: [18, 35, 10749],
      langs: ['ja', 'ko', 'zh'],
    },
    b: {
      name: '獨立影展策展人',
      desc: '藝術電影、獨立製作、歐洲新浪潮、慢節奏敘事的專家。偏好長鏡頭、哲學思辨、非線性敘事。',
      genres: [18, 99, 36],
      langs: ['fr', 'de', 'en', 'it'],
    },
  },
  {
    id: 'horror_vs_romance',
    a: {
      name: '暗夜說書人',
      desc: '恐怖、驚悚、心理懸疑、超自然的專家。偏好氛圍營造、跳嚇以外的恐懼、心理層面的不安。',
      genres: [27, 53, 9648],
      langs: ['en', 'ja', 'ko'],
    },
    b: {
      name: '浪漫劇場導演',
      desc: '愛情、劇情、文藝片的專家。偏好細膩情感、遺憾之美、時代背景下的愛情。',
      genres: [10749, 18, 35],
      langs: ['zh', 'en', 'fr'],
    },
  },
  {
    id: 'anime_vs_docu',
    a: {
      name: '動畫世界旅人',
      desc: '動畫、奇幻、家庭電影的專家。偏好視覺創新、說故事的魔法、適合所有年齡的深度。',
      genres: [16, 14, 10751],
      langs: ['ja', 'en'],
    },
    b: {
      name: '紀錄真實之眼',
      desc: '紀錄片、真實故事改編、社會議題的專家。偏好真實力量、深度調查、人性觀察。',
      genres: [99, 36, 18],
      langs: ['en'],
    },
  },
  {
    id: 'action_vs_classic',
    a: {
      name: '爆米花將軍',
      desc: '動作、冒險、商業大片的專家。偏好爽快節奏、視覺震撼、英雄敘事。',
      genres: [28, 12, 878],
      langs: ['en', 'zh'],
    },
    b: {
      name: '經典時光守護者',
      desc: '2000年前經典電影、影史里程碑的專家。偏好大師作品、影史地位、永恆主題。',
      genres: [18, 35, 10749],
      langs: ['en', 'fr', 'it'],
    },
  },
  {
    id: 'musical_vs_war',
    a: {
      name: '百老匯銀幕魔術師',
      desc: '音樂劇、歌舞片、以音樂為核心的劇情片專家。偏好旋律敘事、舞台魅力、聲音設計。',
      genres: [10402, 35, 18],
      langs: ['en', 'fr'],
    },
    b: {
      name: '戰壕歷史學家',
      desc: '戰爭片、軍事歷史、反戰敘事的專家。偏好真實戰役、人性掙扎、戰爭的荒謬與光榮。',
      genres: [10752, 28, 18, 36],
      langs: ['en', 'de', 'ru'],
    },
  },
  {
    id: 'comedy_vs_thriller',
    a: {
      name: '笑聲煉金術士',
      desc: '喜劇、黑色幽默、諷刺劇的專家。偏好智慧型幽默、社會諷刺、荒謬喜劇。',
      genres: [35, 80, 9648],
      langs: ['en', 'zh', 'fr'],
    },
    b: {
      name: '密室逃脱設計師',
      desc: '心理驚悚、懸疑推理、密室類型的專家。偏好精巧劇情線、不可靠敘事者、結局反轉。',
      genres: [53, 9648, 27],
      langs: ['en', 'ko', 'es'],
    },
  },
  {
    id: 'western_vs_fantasy',
    a: {
      name: '荒野牛仔',
      desc: '西部片、公路電影、荒野敘事的專家。偏好廣闊風景、孤獨英雄、復仇與救贖。',
      genres: [37, 12, 28],
      langs: ['en', 'it'],
    },
    b: {
      name: '中土編年史家',
      desc: '奇幻、史詩、神話敘事的專家。偏好世界觀建構、英雄旅程、古老傳說。',
      genres: [14, 12, 28],
      langs: ['en', 'ja'],
    },
  },
  {
    id: 'biopic_vs_sports',
    a: {
      name: '傳記光影書寫者',
      desc: '傳記片、真實人物改編、歷史劇情的專家。偏好真實故事的力量、時代精神、表演藝術。',
      genres: [36, 18, 10752],
      langs: ['en', 'zh', 'de'],
    },
    b: {
      name: '體育競技場評述員',
      desc: '運動電影、競技敘事、勵志故事的專家。偏好團隊精神、逆轉勝、運動員的人性面。',
      genres: [18, 28],
      langs: ['en', 'ja', 'ko'],
    },
  },
  {
    id: 'superhero_vs_period',
    a: {
      name: '宇宙英雄百科',
      desc: '超級英雄、漫畫改編、宇宙觀敘事的專家。偏好角色弧線、世界觀連動、道德困境。',
      genres: [28, 878, 12],
      langs: ['en'],
    },
    b: {
      name: '宮廷禮儀顧問',
      desc: '時代劇、古裝、宮廷敘事的專家。偏好服裝美學、權力鬥爭、歷史細節考究。',
      genres: [36, 18, 10749],
      langs: ['en', 'fr', 'zh', 'ko'],
    },
  },
]

// ── Prompt Templates ─────────────────────────────────────────────

function buildPlaylistPrompt(expert) {
  return `你是「${expert.name}」，${expert.desc}

請產生 5 組不同的片單測試資料。每組代表一個你想推薦給使用者的電影主題情境。

每組必須包含：
- name: 主題名稱（簡短，中文）
- overviews: 1~2 句描述使用者想看什麼（中文自然語句，像在跟朋友說今晚想看什麼類型的電影）
- playlist_genre_ids: 對應的 TMDB genre ID 陣列
- preferred_languages: 偏好語言代碼陣列
- expected_qualities: 你期望推薦結果應具備的特質（2~3 句，中文）

你的專業領域 genre IDs: ${JSON.stringify(expert.genres)}
你的語言偏好: ${JSON.stringify(expert.langs)}

回傳 JSON 陣列，5 組：
[
  {
    "name": "主題名稱",
    "overviews": ["描述句子"],
    "playlist_genre_ids": [...],
    "preferred_languages": [...],
    "expected_qualities": "..."
  }
]

只回 JSON，不要 markdown fence，不要其他文字。`
}

function buildEvalPrompt(expert, pairMateName, playlist, searchResults) {
  return `你是「${expert.name}」，${expert.desc}

你的 partner「${pairMateName}」為以下片單產生了搜尋意圖：
片單名稱: ${playlist.name}
描述: ${playlist.overviews.join(' ')}
期望特質: ${playlist.expected_qualities}

推薦系統（BERT + SVD + Genome hybrid）回傳了 ${searchResults.length} 部電影：
${searchResults.map((r, i) => `${i+1}. [id=${r.id}] ${r.title} (${(r.release_date||'').slice(0,4)}) score=${r.score} | ${r.overview?.slice(0,100) || 'N/A'}`).join('\n')}

請用你的專業視角評估這些推薦：

1. **relevance** (0-5): 推薦是否精準捕捉了片單意圖？
2. **diversity** (0-5): 年代、語言、子類型是否夠多元？
3. **surprise** (0-5): 是否有意外但你認同的好推薦？
4. **misses**: 你覺得應該出現但遺漏的電影（列出 1~3 部電影名稱+年份）
5. **garbage_ids**: 不應該出現的電影 id 陣列
6. **comment**: 一句話總評

回傳 JSON：
{
  "relevance": 4,
  "diversity": 3,
  "surprise": 4,
  "misses": ["Movie Name (year)"],
  "garbage_ids": [12345],
  "comment": "..."
}

只回 JSON，不要 markdown fence。`
}


// ── Workflow ─────────────────────────────────────────────────────

// Phase 1: Generate playlists — 20 agents in parallel
phase('Generate')

const allPlaylists = await parallel(
  PAIRS.flatMap(pair => [
    async () => {
      const raw = await agent(buildPlaylistPrompt(pair.a), {
        label: `gen:${pair.a.name}`,
        phase: 'Generate',
      })
      let playlists
      try {
        playlists = JSON.parse(raw)
      } catch {
        const m = raw.match(/\[[\s\S]*\]/)
        playlists = m ? JSON.parse(m[0]) : []
      }
      return playlists.map(p => ({ ...p, _pair: pair.id, _side: 'a', _expert: pair.a.name }))
    },
    async () => {
      const raw = await agent(buildPlaylistPrompt(pair.b), {
        label: `gen:${pair.b.name}`,
        phase: 'Generate',
      })
      let playlists
      try {
        playlists = JSON.parse(raw)
      } catch {
        const m = raw.match(/\[[\s\S]*\]/)
        playlists = m ? JSON.parse(m[0]) : []
      }
      return playlists.map(p => ({ ...p, _pair: pair.id, _side: 'b', _expert: pair.b.name }))
    },
  ])
)

const flatPlaylists = allPlaylists.filter(Boolean).flat()
log(`Generated ${flatPlaylists.length} playlists from 20 experts`)

// Phase 2: Search — batch playlists per expert (5 each = 20 agents)
phase('Search')

// Group playlists by expert
const expertGroups = {}
for (const p of flatPlaylists) {
  const key = `${p._pair}_${p._side}`
  if (!expertGroups[key]) expertGroups[key] = []
  expertGroups[key].push(p)
}

const searchResults = await parallel(
  Object.entries(expertGroups).map(([key, playlists]) => async () => {
    const results = []
    for (const playlist of playlists) {
      const body = JSON.stringify({
        overviews: playlist.overviews,
        playlist_genre_ids: playlist.playlist_genre_ids || [],
        preferred_languages: playlist.preferred_languages || [],
        top_k: 10,
      })
      const raw = await agent(
        `Use Bash to run this curl command and return ONLY the raw JSON output, nothing else:\ncurl -s -X POST ${SEARCH_URL} -H "Content-Type: application/json" -d '${body.replace(/'/g, "'\\''")}'`,
        { label: `search:${playlist.name}`, phase: 'Search' }
      )
      try {
        const data = JSON.parse(raw)
        results.push({ playlist, results: data.results || [], llm: data.llm || {} })
      } catch {
        const m = raw.match(/\{[\s\S]*\}/)
        if (m) {
          try {
            const data = JSON.parse(m[0])
            results.push({ playlist, results: data.results || [], llm: data.llm || {} })
          } catch {
            results.push({ playlist, results: [], error: 'parse_error' })
          }
        } else {
          results.push({ playlist, results: [], error: 'no_json' })
        }
      }
    }
    return results
  })
)

const flatSearchResults = searchResults.filter(Boolean).flat()
log(`Completed ${flatSearchResults.filter(r => r && r.results.length > 0).length}/${flatSearchResults.length} searches`)

// Phase 3: Cross-evaluate — each expert reviews their pair-mate's results
phase('Cross-Evaluate')

const evaluations = await parallel(
  PAIRS.flatMap(pair => {
    // a evaluates b's playlists, b evaluates a's playlists
    const bPlaylists = flatSearchResults.filter(r => r && r.playlist._pair === pair.id && r.playlist._side === 'b' && r.results.length > 0)
    const aPlaylists = flatSearchResults.filter(r => r && r.playlist._pair === pair.id && r.playlist._side === 'a' && r.results.length > 0)

    return [
      async () => {
        const results = []
        for (const sr of bPlaylists) {
          const raw = await agent(buildEvalPrompt(pair.a, pair.b.name, sr.playlist, sr.results), {
            label: `eval:${pair.a.name}→${sr.playlist.name}`,
            phase: 'Cross-Evaluate',
          })
          let score
          try {
            score = JSON.parse(raw)
          } catch {
            const m = raw.match(/\{[\s\S]*\}/)
            score = m ? JSON.parse(m[0]) : null
          }
          if (score) {
            results.push({
              evaluator: pair.a.name,
              generator: pair.b.name,
              pair: pair.id,
              playlist: sr.playlist.name,
              ...score,
            })
          }
        }
        return results
      },
      async () => {
        const results = []
        for (const sr of aPlaylists) {
          const raw = await agent(buildEvalPrompt(pair.b, pair.a.name, sr.playlist, sr.results), {
            label: `eval:${pair.b.name}→${sr.playlist.name}`,
            phase: 'Cross-Evaluate',
          })
          let score
          try {
            score = JSON.parse(raw)
          } catch {
            const m = raw.match(/\{[\s\S]*\}/)
            score = m ? JSON.parse(m[0]) : null
          }
          if (score) {
            results.push({
              evaluator: pair.b.name,
              generator: pair.a.name,
              pair: pair.id,
              playlist: sr.playlist.name,
              ...score,
            })
          }
        }
        return results
      },
    ]
  })
)

const flatEvals = evaluations.filter(Boolean).flat()
log(`Completed ${flatEvals.length} cross-evaluations`)

// Phase 4: Report
phase('Report')

// Aggregate by pair
const pairReports = PAIRS.map(pair => {
  const pairEvals = flatEvals.filter(e => e.pair === pair.id)
  if (!pairEvals.length) return null

  const avg = (key) => {
    const vals = pairEvals.filter(e => e[key] != null).map(e => Number(e[key]))
    return vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : 'N/A'
  }

  const allMisses = pairEvals.flatMap(e => e.misses || [])
  const allGarbage = pairEvals.flatMap(e => e.garbage_ids || [])

  return {
    pair: pair.id,
    experts: [pair.a.name, pair.b.name],
    eval_count: pairEvals.length,
    avg_relevance: avg('relevance'),
    avg_diversity: avg('diversity'),
    avg_surprise: avg('surprise'),
    common_misses: allMisses.slice(0, 5),
    garbage_count: allGarbage.length,
    evaluations: pairEvals,
  }
}).filter(Boolean)

// Overall stats
const allRelevance = flatEvals.filter(e => e.relevance != null).map(e => Number(e.relevance))
const allDiversity = flatEvals.filter(e => e.diversity != null).map(e => Number(e.diversity))
const allSurprise = flatEvals.filter(e => e.surprise != null).map(e => Number(e.surprise))

const overall = {
  total_playlists: flatPlaylists.length,
  total_searches: flatSearchResults.filter(r => r && r.results.length > 0).length,
  total_evaluations: flatEvals.length,
  overall_avg_relevance: allRelevance.length ? (allRelevance.reduce((a, b) => a + b, 0) / allRelevance.length).toFixed(2) : 'N/A',
  overall_avg_diversity: allDiversity.length ? (allDiversity.reduce((a, b) => a + b, 0) / allDiversity.length).toFixed(2) : 'N/A',
  overall_avg_surprise: allSurprise.length ? (allSurprise.reduce((a, b) => a + b, 0) / allSurprise.length).toFixed(2) : 'N/A',
  total_garbage: flatEvals.flatMap(e => e.garbage_ids || []).length,
}

return {
  summary: overall,
  pair_reports: pairReports,
  raw_evaluations: flatEvals,
  playlists: flatPlaylists,
}
