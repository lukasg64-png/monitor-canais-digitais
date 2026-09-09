import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = '''          <div class="section-title">
            <span>📈 Curva Horária Acumulada vs Meta e Passado (Visão Panorâmica 00:00 às 23:00)</span>
          </div>
          <span style="font-size: 11.5px; color: var(--text-tertiary);" id="chart-curve-sub">00:00 às 23:00 • 24 Horas Completo</span>
        </div>
        <div class="chart-canvas-wrap" style="height: 380px;">'''

replacement = '''          <div class="section-title">
            <span>📈 Curva Horária Acumulada vs Meta e Passado (Visão Panorâmica 00:00 às 23:00)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <button class="btn-cockpit-guide" id="btn-toggle-milestone-calc" onclick="toggleMilestoneCalc()" title="Ver metodologia e cálculo de projeção">
              <span>🧮 Detalhes do Cálculo</span>
            </button>
            <span style="font-size: 11.5px; color: var(--text-tertiary);" id="chart-curve-sub">00:00 às 23:00 • 24 Horas Completo</span>
          </div>
        </div>

        <!-- Cardzinho Executivo de Previsão de Bater a Meta -->
        <div id="milestone-widget-container"></div>

        <!-- Painel Didático de Metodologia do Cálculo (Collapsible) -->
        <div class="milestone-calc-drawer" id="milestone-calc-drawer" style="display: none;">
          <div style="margin-bottom: 10px; font-weight: 700; font-size: 12.5px; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
            <span>💡 Como funciona a Previsão de Horário da Meta &amp; a Linha Vertical no Gráfico?</span>
          </div>
          <div class="calc-drawer-content">
            <div class="calc-step">
              <span class="calc-step-num">1</span>
              <div>
                <strong style="color: var(--text-primary);">Curva Ponderada Intraday:</strong>
                O modelo respeita o histórico real de distribuição horária das Farmácias São João (não faz divisão linear simplista). Ele considera que o fluxo de vendas varia conforme o pico de tráfego.
              </div>
            </div>
            <div class="calc-step">
              <span class="calc-step-num">2</span>
              <div>
                <strong style="color: var(--text-primary);">Interpolação no Ponto de Equilíbrio:</strong>
                Projeta o faturamento minuto a minuto até as 23h59 com base no pacing atual. No ponto exato em que a curva verde projetada cruza o valor da Meta do Dia, calcula-se o horário previsto de superação.
              </div>
            </div>
            <div class="calc-step">
              <span class="calc-step-num">3</span>
              <div>
                <strong style="color: var(--text-primary);">Linha Vertical nos Gráficos:</strong>
                A linha tracejada vertical com selo no topo indica exatamente esse instante no tempo nos dois gráficos abaixo, facilitando a decisão tática de investimentos de mídia e ativação comercial.
              </div>
            </div>
          </div>
        </div>

        <div class="chart-canvas-wrap" style="height: 380px;">'''

if target in html:
    html = html.replace(target, replacement, 1)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML markup replaced successfully.")
else:
    print("ERROR: Target HTML not found.")
