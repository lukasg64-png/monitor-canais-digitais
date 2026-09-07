import sys

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Inserir Mobile Engine CSS antes de </style>
mobile_css = '''
    /* =========================================================
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

    @media (max-width: 768px) {
      .app-container {
        padding: 8px 10px 30px 10px !important;
        gap: 12px !important;
      }

      .mobile-table-hint {
        display: block !important;
      }

      /* Header Mobile Compact */
      .nav-header {
        padding: 12px 14px !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 10px !important;
      }

      .brand-group {
        width: 100% !important;
        justify-content: flex-start !important;
        gap: 10px !important;
      }

      .brand-logo-mark {
        width: 38px !important;
        height: 38px !important;
        font-size: 14px !important;
      }

      .brand-title {
        font-size: 15px !important;
        flex-wrap: wrap !important;
        gap: 4px !important;
      }

      .brand-subtitle {
        font-size: 10.5px !important;
        line-height: 1.3 !important;
      }

      .header-actions {
        width: 100% !important;
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 6px !important;
      }

      .header-actions .badge-status {
        justify-content: center !important;
        font-size: 10px !important;
        padding: 5px 6px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
      }

      .header-actions .btn-action-apple {
        justify-content: center !important;
        font-size: 10.5px !important;
        padding: 6px 8px !important;
        width: 100% !important;
      }

      .theme-toggle-btn {
        grid-column: span 2 !important;
        width: 100% !important;
        height: 32px !important;
        border-radius: var(--radius-pill) !important;
      }

      /* Storytelling / Diagnóstico Mobile */
      .storytelling-card {
        padding: 12px 14px !important;
      }

      .story-headline {
        font-size: 14px !important;
        line-height: 1.35 !important;
      }

      .story-body {
        font-size: 11.5px !important;
        line-height: 1.45 !important;
      }

      .story-estoque-box {
        padding: 10px 12px !important;
      }

      .story-grid {
        grid-template-columns: 1fr !important;
        gap: 8px !important;
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
      .header-actions {
        grid-template-columns: 1fr !important;
      }
      .theme-toggle-btn {
        grid-column: span 1 !important;
      }
    }
'''

if '</style>' in html:
    html = html.replace('</style>', mobile_css + '\n  </style>')
    print("Mobile CSS engine successfully added before </style>!")
else:
    print("ERROR: </style> tag not found!")
    sys.exit(1)

# 2. Inserir hint acima da tabela
target_table = '<div class="table-container">'
hint_html = '<div class="mobile-table-hint">👉 Deslize para o lado para ver Saldo, Densidade e Causa-Raiz</div>\n      <div class="table-container">'

if target_table in html:
    html = html.replace(target_table, hint_html, 1)
    print("Table mobile hint successfully added!")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("index.html updated with Mobile Engine!")
