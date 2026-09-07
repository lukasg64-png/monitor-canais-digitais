import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Inserir botão de toggle dentro do storytelling-card
target_after_estoque = '''        <div id="story-estoque" style="font-size: 12.5px; color: var(--text-primary); line-height: 1.55;">...</div>
      </div>'''

replacement_with_toggle = '''        <div id="story-estoque" style="font-size: 12.5px; color: var(--text-primary); line-height: 1.55;">...</div>
      </div>

      <button class="story-toggle-btn" id="story-toggle-btn" onclick="toggleMobileStory()">
        <span id="story-toggle-icon">📖</span>
        <span id="story-toggle-text">Ver Detalhes do Diagnóstico e Frentes de Gap ▾</span>
      </button>'''

if target_after_estoque in html and 'story-toggle-btn' not in html:
    html = html.replace(target_after_estoque, replacement_with_toggle)
    print("Story toggle button added to HTML!")

# 2. Atualizar CSS do mobile
pattern_mobile_css = r'/\* =========================================================\s*ULTRA-RESPONSIVE MOBILE ENGINE[\s\S]*?</style>'

new_mobile_css = '''/* =========================================================
       ULTRA-RESPONSIVE MOBILE ENGINE (SMARTPHONE & TABLET)
       Apple iOS Native Design System
       ========================================================= */
    .mobile-table-hint {
      display: none;
      font-size: 11px;
      font-weight: 600;
      color: var(--apple-blue);
      background: var(--apple-blue-soft);
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      margin-bottom: 8px;
      text-align: center;
    }

    .story-toggle-btn {
      display: none;
      align-items: center;
      justify-content: center;
      gap: 6px;
      width: 100%;
      padding: 9px 12px;
      background: var(--surface-hover);
      border: 1px solid var(--border);
      border-radius: var(--radius-pill);
      font-size: 11.5px;
      font-weight: 600;
      color: var(--apple-blue);
      cursor: pointer;
      margin-top: 10px;
      transition: all 0.2s ease;
    }

    .story-toggle-btn:active {
      transform: scale(0.98);
      background: var(--apple-blue-soft);
    }

    @media (max-width: 768px) {
      .app-container {
        padding: 8px 10px 30px 10px !important;
        gap: 12px !important;
      }

      .mobile-table-hint {
        display: block !important;
      }

      .story-toggle-btn {
        display: flex !important;
      }

      /* Compact Horizontal Ribbon Header */
      .nav-header {
        padding: 10px 12px !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 8px !important;
      }

      .brand-group {
        width: 100% !important;
        justify-content: flex-start !important;
        gap: 8px !important;
      }

      .brand-logo-mark {
        width: 34px !important;
        height: 34px !important;
        font-size: 13px !important;
      }

      .brand-title {
        font-size: 14.5px !important;
        flex-wrap: wrap !important;
        gap: 4px !important;
      }

      .brand-subtitle {
        display: none !important; /* Salva espaço crítico no mobile */
      }

      .header-actions {
        width: 100% !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        gap: 6px !important;
        padding-bottom: 2px !important;
      }

      .header-actions::-webkit-scrollbar {
        display: none;
      }

      .header-actions .badge-status, .header-actions .btn-action-apple {
        flex: 0 0 auto !important;
        font-size: 10.5px !important;
        padding: 5px 10px !important;
        white-space: nowrap !important;
      }

      .theme-toggle-btn {
        flex: 0 0 auto !important;
        width: 32px !important;
        height: 32px !important;
        border-radius: var(--radius-pill) !important;
      }

      /* Storytelling / Diagnóstico Mobile Compact */
      .storytelling-card {
        padding: 12px 14px !important;
      }

      .story-headline {
        font-size: 14px !important;
        line-height: 1.35 !important;
        margin-bottom: 8px !important;
      }

      .story-estoque-box {
        padding: 10px 12px !important;
        margin: 8px 0 !important;
      }

      /* Colapsa parágrafos longos por padrão no mobile para os KPIs subirem */
      #story-pacing, #story-janelas, .story-grid {
        display: none;
      }

      #story-pacing.mobile-open, #story-janelas.mobile-open {
        display: block !important;
        font-size: 11.5px !important;
        line-height: 1.45 !important;
        margin-top: 6px !important;
      }

      .story-grid.mobile-open {
        display: grid !important;
        grid-template-columns: 1fr !important;
        gap: 8px !important;
        margin-top: 10px !important;
      }

      .story-box {
        padding: 10px 12px !important;
      }

      .story-item {
        padding: 6px 0 !important;
      }

      /* Channel Selector: 2x2 Clean Grid on Mobile */
      .channel-nav-container {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 8px !important;
      }

      .channel-tab {
        padding: 10px 12px !important;
        gap: 4px !important;
        border-radius: 12px !important;
      }

      .channel-name {
        font-size: 12.5px !important;
      }

      .channel-badge {
        font-size: 9px !important;
        padding: 2px 5px !important;
      }

      .channel-sales {
        font-size: 17px !important;
        letter-spacing: -0.4px !important;
      }

      .channel-meta-sub {
        font-size: 9.5px !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 1px !important;
      }

      .channel-deltas-line {
        font-size: 9px !important;
        gap: 6px !important;
        flex-wrap: wrap !important;
        padding-top: 4px !important;
      }

      /* Top Executive KPI Grid: 2x2 Grid on Mobile */
      .kpi-grid {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 8px !important;
      }

      .kpi-card {
        padding: 10px 12px !important;
        gap: 5px !important;
        border-radius: 12px !important;
      }

      .kpi-title {
        font-size: 10px !important;
        line-height: 1.2 !important;
      }

      .kpi-value {
        font-size: 18px !important;
        letter-spacing: -0.4px !important;
      }

      .kpi-footer-row {
        font-size: 9px !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 2px !important;
      }

      /* Radar de Mix & Eficiência */
      .mix-grid {
        grid-template-columns: 1fr !important;
        gap: 8px !important;
      }

      .mix-card {
        padding: 12px !important;
      }

      /* Janelas Comparativas */
      .windows-grid {
        grid-template-columns: 1fr !important;
        gap: 8px !important;
      }

      /* Charts Section */
      .charts-split-grid {
        grid-template-columns: 1fr !important;
        gap: 12px !important;
      }

      .chart-card {
        padding: 12px 10px !important;
      }

      .chart-canvas-wrap {
        height: 220px !important;
      }

      /* Gauges Cockpit */
      .gauges-container {
        display: grid !important;
        grid-template-columns: repeat(3, 1fr) !important;
        gap: 4px !important;
      }

      .gauge-card {
        padding: 8px 4px !important;
      }

      .gauge-title {
        font-size: 9.5px !important;
      }

      .gauge-value {
        font-size: 12.5px !important;
      }

      .gauge-chip {
        font-size: 8.5px !important;
        padding: 2px 4px !important;
      }

      /* Matrix Toolbar on Mobile */
      .matrix-toolbar {
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 8px !important;
      }

      .apple-segmented-control {
        width: 100% !important;
        overflow-x: auto !important;
        justify-content: flex-start !important;
        -webkit-overflow-scrolling: touch !important;
        padding-bottom: 2px !important;
      }

      .segmented-btn {
        padding: 6px 10px !important;
        font-size: 11px !important;
      }

      .filter-actions-group {
        width: 100% !important;
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
      }

      .pill-filter-btn {
        padding: 5px 8px !important;
        font-size: 10.5px !important;
        flex: 1 !important;
        text-align: center !important;
      }

      .apple-search-input {
        width: 100% !important;
        min-width: 0 !important;
        font-size: 11px !important;
        padding: 6px 10px !important;
      }

      /* Tables on Mobile */
      .table-container {
        max-height: 400px !important;
        -webkit-overflow-scrolling: touch !important;
      }

      table.apple-table th, table.apple-table td {
        padding: 7px 9px !important;
        font-size: 10.5px !important;
        white-space: nowrap !important;
      }
    }

    @media (max-width: 480px) {
      .channel-sales {
        font-size: 15px !important;
      }
      .kpi-value {
        font-size: 16px !important;
      }
      .gauges-container {
        grid-template-columns: 1fr !important;
        gap: 8px !important;
      }
      .gauge-card {
        padding: 10px !important;
      }
    }
  </style>'''

html = re.sub(pattern_mobile_css, new_mobile_css, html)

# 3. Inserir função toggleMobileStory no JS
js_func = '''
    function toggleMobileStory() {
      const p = document.getElementById('story-pacing');
      const j = document.getElementById('story-janelas');
      const g = document.querySelector('.story-grid');
      const btn = document.getElementById('story-toggle-text');
      const icon = document.getElementById('story-toggle-icon');
      if (!p) return;
      const isOpen = p.classList.contains('mobile-open');
      if (isOpen) {
        p.classList.remove('mobile-open');
        if (j) j.classList.remove('mobile-open');
        if (g) g.classList.remove('mobile-open');
        if (btn) btn.innerText = 'Ver Detalhes do Diagnóstico e Frentes de Gap ▾';
        if (icon) icon.innerText = '📖';
      } else {
        p.classList.add('mobile-open');
        if (j) j.classList.add('mobile-open');
        if (g) g.classList.add('mobile-open');
        if (btn) btn.innerText = 'Ocultar Detalhes do Diagnóstico ▴';
        if (icon) icon.innerText = '✕';
      }
    }
'''

if 'function toggleMobileStory' not in html:
    html = html.replace('function setLevel(', js_func + '\n    function setLevel(')
    print("toggleMobileStory JS function inserted!")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("SUCCESS: index.html fully optimized for Mobile iOS UX!")
