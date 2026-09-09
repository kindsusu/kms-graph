import { Component, type ErrorInfo, type ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import GraphCanvas from './graph/GraphCanvas';
import { isSafeExternalUrl, loadPayload } from './data';
import { writeSelectionHistory } from './navigation';
import type { GraphStats, ItemKind, KnowledgeItem, KnowledgePayload, KnowledgeRelation } from './model';

type View = 'graph' | 'list';
type Theme = 'light' | 'dark';
type Sort = 'name' | 'updated' | 'connections';
const PAGE_SIZE = 24;
const KIND_LABEL: Record<ItemKind, string> = { document: '지식·문서', tool: '업무 도구', ai_asset: 'AI 자산' };
const KIND_SHORT: Record<ItemKind, string> = { document: '문서', tool: '도구', ai_asset: 'AI' };

function Icon({ name }: { name: 'library' | 'document' | 'tool' | 'sparkles' | 'graph' | 'search' | 'theme' | 'close' | 'external' }) {
  const paths: Record<typeof name, ReactNode> = {
    library: <><path d="M4 5h16M4 12h16M4 19h16" /></>,
    document: <><path d="M6 3h9l3 3v15H6z" /><path d="M9 10h6M9 14h6M9 18h4" /></>,
    tool: <><path d="M14.5 6.5a4 4 0 0 0-5 5L4 17l3 3 5.5-5.5a4 4 0 0 0 5-5l-2.5 2.5-3-3z" /></>,
    sparkles: <><path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2zM18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8zM6 14l.8 2.2L9 17l-2.2.8L6 20l-.8-2.2L3 17l2.2-.8z" /></>,
    graph: <><circle cx="6" cy="6" r="2" /><circle cx="18" cy="8" r="2" /><circle cx="10" cy="18" r="2" /><path d="m8 7 8 1M7 8l2 8m3-1 5-5" /></>,
    search: <><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" /></>,
    theme: <><path d="M20 15.3A8 8 0 1 1 8.7 4 6.5 6.5 0 0 0 20 15.3Z" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    external: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 13v7H4V6h7" /></>,
  };
  return <svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

class GraphBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('GraphCanvas failed', error, info); }
  render() {
    return this.state.failed ? (
      <div className="state-card"><strong>연결 그래프를 표시할 수 없습니다.</strong><p>목록 보기에서 자료를 계속 탐색할 수 있습니다. 페이지를 새로 고쳐 다시 시도해 주세요.</p></div>
    ) : this.props.children;
  }
}

function useHashSelection(validIds: ReadonlySet<string>) {
  const read = () => {
    const match = location.hash.match(/^#item=(.+)$/);
    if (!match) return null;
    try { const id = decodeURIComponent(match[1]); return validIds.has(id) ? id : null; } catch { return null; }
  };
  const [selectedId, setState] = useState<string | null>(read);
  useEffect(() => {
    const sync = () => setState(read());
    addEventListener('hashchange', sync);
    return () => removeEventListener('hashchange', sync);
  }, [validIds]);
  const select = (id: string | null, replace = false) => {
    if (id === selectedId) return;
    writeSelectionHistory(history, location.pathname, location.search, id, replace);
    setState(id);
  };
  return [selectedId, select] as const;
}

function DetailPanel({ item, relations, byId, onClose, onNavigate }: {
  item: KnowledgeItem; relations: KnowledgeRelation[]; byId: ReadonlyMap<string, KnowledgeItem>;
  onClose: () => void; onNavigate: (id: string) => void;
}) {
  const related = relations.filter((relation) => relation.source === item.id || relation.target === item.id);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { closeRef.current?.focus(); }, [item.id]);
  return <aside className="detail-panel" aria-labelledby="detail-title">
    <div className="detail-head"><span className={`kind-pill ${item.kind}`}>{KIND_SHORT[item.kind]} · {item.subtype || '미분류'}</span><button ref={closeRef} className="icon-button" onClick={onClose} aria-label="상세 닫기"><Icon name="close" /></button></div>
    <h2 id="detail-title">{item.title}</h2><p className="lede">{item.description || '설명이 등록되지 않았습니다.'}</p>
    <dl className="metadata">
      <div><dt>담당</dt><dd>{item.owner || '미등록'}</dd></div><div><dt>부서</dt><dd>{item.department || '미등록'}</dd></div>
      <div><dt>업무 분야</dt><dd>{item.domain || '미분류'}</dd></div><div><dt>상태</dt><dd>{item.status || '미등록'}</dd></div>
      {item.version && <div><dt>버전</dt><dd>{item.version}</dd></div>}{item.updatedAt && <div><dt>업데이트</dt><dd>{item.updatedAt}</dd></div>}
    </dl>
    <div className="tags" aria-label="태그">{item.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>
    {item.body && <section><h3>내용</h3><p className="body-copy">{item.body}</p></section>}
    {item.kind === 'ai_asset' && item.subtype === '프롬프트' && item.prompt && <section><h3>프롬프트</h3><pre className="prompt">{item.prompt}</pre></section>}
    {isSafeExternalUrl(item.url) && <a className="primary-link" href={item.url} target="_blank" rel="noopener noreferrer">원본 열기 <Icon name="external" /></a>}
    <section><h3>연결된 자료 <span>{related.length}</span></h3>
      {related.length ? <ul className="relations">{related.map((relation) => {
        const outgoing = relation.source === item.id;
        const other = byId.get(outgoing ? relation.target : relation.source);
        return other && <li key={relation.id}><button onClick={() => onNavigate(other.id)}><span className="relation-direction">{outgoing ? '→' : '←'} {relation.label}</span><strong>{other.title}</strong></button></li>;
      })}</ul> : <p className="muted">표시할 관계가 없습니다.</p>}
    </section>
  </aside>;
}

function Workspace({ payload }: { payload: KnowledgePayload }) {
  const ids = useMemo(() => new Set(payload.items.map((item) => item.id)), [payload.items]);
  const byId = useMemo(() => new Map(payload.items.map((item) => [item.id, item])), [payload.items]);
  const [selectedId, select] = useHashSelection(ids);
  const [view, setView] = useState<View>('list');
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState<ItemKind | 'all'>('all');
  const [domain, setDomain] = useState('all');
  const [sort, setSort] = useState<Sort>('name');
  const [depth, setDepth] = useState<0 | 1 | 2>(0);
  const [page, setPage] = useState(1);
  const [focusNonce, setFocusNonce] = useState(0);
  const [stats, setStats] = useState<GraphStats>({ visibleNodes: payload.items.length, visibleEdges: payload.relations.length, layoutRunning: true });
  const [theme, setTheme] = useState<Theme>(() => { try { return localStorage.getItem('kms-theme') === 'dark' ? 'dark' : 'light'; } catch { return 'light'; } });
  const searchRef = useRef<HTMLInputElement>(null);
  const selectionTriggerRef = useRef<HTMLElement | null>(null);
  const domains = useMemo(() => [...new Set(payload.items.map((item) => item.domain))].sort((a, b) => a.localeCompare(b, 'ko')), [payload.items]);
  const relationCount = useMemo(() => {
    const neighbors = new Map(payload.items.map((item) => [item.id, new Set<string>()]));
    payload.relations.forEach((relation) => { neighbors.get(relation.source)?.add(relation.target); neighbors.get(relation.target)?.add(relation.source); });
    return new Map([...neighbors].map(([id, related]) => [id, related.size]));
  }, [payload.items, payload.relations]);

  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem('kms-theme', theme); } catch { /* Storage can be disabled by policy. */ } }, [theme]);
  useEffect(() => setPage(1), [query, kind, domain, sort]);
  useEffect(() => {
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') { event.preventDefault(); searchRef.current?.focus(); }
      if (event.key === 'Escape' && query) { setQuery(''); searchRef.current?.focus(); }
    };
    addEventListener('keydown', keyboard); return () => removeEventListener('keydown', keyboard);
  }, [query]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase('ko');
    return payload.items.filter((item) => {
      if (kind !== 'all' && item.kind !== kind) return false;
      if (domain !== 'all' && item.domain !== domain) return false;
      if (!needle) return true;
      return [item.title, item.description, item.body, item.prompt, item.owner, ...item.tags].filter(Boolean).join('\n').toLocaleLowerCase('ko').includes(needle);
    }).sort((a, b) => {
      if (sort === 'connections') return (relationCount.get(b.id) ?? 0) - (relationCount.get(a.id) ?? 0) || a.title.localeCompare(b.title, 'ko');
      if (sort === 'updated') return (b.updatedAt ?? '').localeCompare(a.updatedAt ?? '') || a.title.localeCompare(b.title, 'ko');
      return a.title.localeCompare(b.title, 'ko');
    });
  }, [payload.items, query, kind, domain, sort, relationCount]);
  const visibleIds = useMemo(() => new Set(filtered.map((item) => item.id)), [filtered]);
  const selected = selectedId ? byId.get(selectedId) ?? null : null;
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const shown = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => { if (selectedId && !visibleIds.has(selectedId)) { select(null, true); setDepth(0); } }, [selectedId, visibleIds]);
  const chooseKind = (next: ItemKind | 'all') => { setKind(next); setView('list'); };
  const selectFrom = (id: string, trigger?: HTMLElement | null) => { selectionTriggerRef.current = trigger ?? document.activeElement as HTMLElement | null; select(id); };
  const closeDetail = () => { const trigger = selectionTriggerRef.current; select(null); requestAnimationFrame(() => trigger?.isConnected && trigger.focus()); };
  const navigateRelation = (id: string) => { setQuery(''); setKind('all'); setDomain('all'); select(id); };
  const showInGraph = (id: string, trigger?: HTMLElement | null) => { selectionTriggerRef.current = trigger ?? document.activeElement as HTMLElement | null; select(id); setView('graph'); setFocusNonce((value) => value + 1); };

  return <div className={`app-shell ${selected ? 'has-detail' : ''}`}>
    <header className="topbar"><button className="brand" onClick={() => chooseKind('all')}><span className="brand-mark">K</span><span>{payload.title}</span></button>
      {payload.isDemo && <span className="demo-badge">개발 샘플 · {payload.items.length}개</span>}
      <button className="theme-button" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} aria-label={`${theme === 'light' ? '어두운' : '밝은'} 테마로 전환`} aria-pressed={theme === 'dark'}><Icon name="theme" /></button>
    </header>
    <nav className="sidebar" aria-label="자료 유형">
      <p className="nav-label">라이브러리</p>
      <button className={kind === 'all' && view === 'list' ? 'active' : ''} onClick={() => chooseKind('all')} aria-current={kind === 'all' && view === 'list' ? 'page' : undefined}><span><Icon name="library" /></span>모든 자료<small>{payload.items.length}</small></button>
      {(Object.keys(KIND_LABEL) as ItemKind[]).map((value) => <button key={value} className={kind === value ? 'active' : ''} onClick={() => chooseKind(value)} aria-current={kind === value ? 'page' : undefined}><span><Icon name={value === 'document' ? 'document' : value === 'tool' ? 'tool' : 'sparkles'} /></span>{KIND_LABEL[value]}<small>{payload.items.filter((item) => item.kind === value).length}</small></button>)}
      <div className="nav-separator" /><p className="nav-label">탐색</p>
      <button className={view === 'graph' ? 'active' : ''} onClick={() => setView('graph')} aria-current={view === 'graph' ? 'page' : undefined}><span><Icon name="graph" /></span>연결 그래프</button>
    </nav>
    <main className="workspace">
      <div className="workspace-head"><div><p className="eyebrow">KNOWLEDGE LIBRARY</p><h1>{view === 'graph' ? '연결 그래프' : kind === 'all' ? '모든 자료' : KIND_LABEL[kind]}</h1><p className="workspace-summary">{filtered.length.toLocaleString()}개 자료 · {payload.relations.length.toLocaleString()}개 연결</p></div>
        <div className="view-toggle" aria-label="보기 방식"><button className={view === 'graph' ? 'active' : ''} onClick={() => setView('graph')}>그래프</button><button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}>목록</button></div>
      </div>
      <div className="filterbar"><label className="search"><span><Icon name="search" /></span><input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="제목, 내용, 담당자, 태그 검색" aria-label="자료 검색" />{query && <button onClick={() => setQuery('')} aria-label="검색어 지우기"><Icon name="close" /></button>}<kbd>/</kbd></label>
        <select value={kind} onChange={(event) => setKind(event.target.value as ItemKind | 'all')} aria-label="자료 유형"><option value="all">모든 유형</option>{(Object.keys(KIND_LABEL) as ItemKind[]).map((value) => <option key={value} value={value}>{KIND_LABEL[value]}</option>)}</select>
        <select value={domain} onChange={(event) => setDomain(event.target.value)} aria-label="업무 분야"><option value="all">모든 업무 분야</option>{domains.map((value) => <option key={value} value={value}>{value || '미분류'}</option>)}</select>
        <select value={sort} onChange={(event) => setSort(event.target.value as Sort)} aria-label="정렬"><option value="name">이름순</option><option value="updated">최신순</option><option value="connections">연결 많은 순</option></select>
      </div>
      <div className="content-stack"><section className={`graph-pane ${view !== 'graph' ? 'view-hidden' : ''}`} aria-label="연결 그래프">
        <div className="graph-toolbar"><span><strong>{stats.visibleNodes.toLocaleString()}</strong>개 자료 · <strong>{stats.visibleEdges.toLocaleString()}</strong>개 연결 {stats.layoutRunning && <i>배치 중</i>}</span>
          <div className="depth-control" aria-label="연결 범위"><button className={depth === 0 ? 'active' : ''} onClick={() => setDepth(0)}>전체</button><button disabled={!selected} className={depth === 1 ? 'active' : ''} onClick={() => setDepth(1)}>1단계</button><button disabled={!selected} className={depth === 2 ? 'active' : ''} onClick={() => setDepth(2)}>2단계</button>{selected && <button onClick={() => setFocusNonce((value) => value + 1)}>선택으로 이동</button>}</div>
        </div>
        <GraphBoundary><GraphCanvas items={payload.items} relations={payload.relations} selectedId={selectedId} onSelect={(id) => id ? selectFrom(id) : closeDetail()} visibleIds={visibleIds} localDepth={depth} focusRequest={selectedId ? { id: selectedId, nonce: focusNonce } : null} onStats={setStats} /></GraphBoundary>
        {!filtered.length && <div className="empty empty-overlay"><strong>조건에 맞는 자료가 없습니다.</strong><p>검색어를 지우거나 필터 범위를 넓혀 보세요.</p><button onClick={() => { setQuery(''); setKind('all'); setDomain('all'); }}>필터 초기화</button></div>}
        <div className="graph-legend" aria-label="자료 유형 범례"><span><i className="kind-dot document" />문서</span><span><i className="kind-dot tool" />도구</span><span><i className="kind-dot ai_asset" />AI 자산</span></div>
      </section><section className={`list-pane ${view !== 'list' ? 'view-hidden' : ''}`} aria-label="자료 목록">
        <div className="list-summary"><span><strong>{filtered.length.toLocaleString()}</strong>개 자료</span><span>{page} / {pages} 페이지</span></div>
        {shown.length ? <div className="item-table" role="table" aria-label="자료 목록"><div className="table-header" role="row"><span role="columnheader">자료명</span><span role="columnheader">유형</span><span role="columnheader">업무 분야</span><span role="columnheader">담당</span><span role="columnheader">연결 자료</span><span role="columnheader">업데이트</span><span role="columnheader"><span className="sr-only">그래프 작업</span></span></div>{shown.map((item) => <div role="row" key={item.id} className={`table-row ${item.id === selectedId ? 'selected' : ''}`}>
          <span role="cell"><button className="row-title" onClick={(event) => selectFrom(item.id, event.currentTarget)}><span className={`kind-dot ${item.kind}`} /><span><strong>{item.title}</strong><small>{item.description || '설명 미등록'}</small></span></button></span>
          <span className={`kind-text ${item.kind}`} role="cell">{KIND_SHORT[item.kind]}</span><span role="cell" className="cell-secondary">{item.domain || '미분류'}</span><span role="cell" className="cell-secondary">{item.owner || '미등록'}</span><span role="cell" className="connection-count">{relationCount.get(item.id) ?? 0}</span><span role="cell" className="cell-secondary">{item.updatedAt || '—'}</span>
          <span role="cell"><button className="graph-jump" onClick={(event) => showInGraph(item.id, event.currentTarget)} aria-label={`${item.title}을 그래프에서 보기`} title="그래프에서 보기"><Icon name="graph" /></button></span>
        </div>)}</div> : <div className="empty"><strong>조건에 맞는 자료가 없습니다.</strong><button onClick={() => { setQuery(''); setKind('all'); setDomain('all'); }}>필터 초기화</button></div>}
        {pages > 1 && <div className="pagination"><button disabled={page === 1} onClick={() => setPage((value) => value - 1)}>이전</button><span>{(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)}</span><button disabled={page === pages} onClick={() => setPage((value) => value + 1)}>다음</button></div>}
      </section></div>
    </main>
    {selected && <DetailPanel item={selected} relations={payload.relations} byId={byId} onClose={closeDetail} onNavigate={navigateRelation} />}
  </div>;
}

export default function App() {
  const [state, setState] = useState<{ payload?: KnowledgePayload; error?: string }>({});
  useEffect(() => { let active = true; loadPayload().then((payload) => active && setState({ payload })).catch((error) => active && setState({ error: error instanceof Error ? error.message : '알 수 없는 오류' })); return () => { active = false; }; }, []);
  if (state.error) return <main className="fatal"><span className="brand-mark">K</span><p className="eyebrow">DATA ERROR</p><h1>지식 데이터를 열 수 없습니다.</h1><p>{state.error}</p><p className="muted">게시 담당자에게 빌드 결과와 데이터 형식을 확인해 달라고 요청하세요.</p></main>;
  if (!state.payload) return <main className="loading"><span className="spinner" /><span>지식 지도를 준비하는 중…</span></main>;
  if (!state.payload.items.length) return <main className="fatal"><span className="brand-mark">K</span><h1>아직 등록된 자료가 없습니다.</h1><p>수집 원본을 확인한 뒤 사이트를 다시 빌드해 주세요.</p></main>;
  return <Workspace payload={state.payload} />;
}
