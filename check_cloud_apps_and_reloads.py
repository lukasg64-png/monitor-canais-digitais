import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"

async def inspect_cloud():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        
        print("Navegando para o Qlik Cloud...", flush=True)
        await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
        
        try:
            user_input = await page.wait_for_selector('#username', timeout=10000)
            if user_input:
                print("Efetuando login SSO...", flush=True)
                await page.fill('#username', USERNAME)
                await page.fill('#password', PASSWORD)
                await page.click('#kc-login')
                await page.wait_for_url(f"**{QLIK_CLOUD_HOST}/analytics/**", timeout=60000)
                await page.wait_for_timeout(3000)
                await context.storage_state(path=STORAGE_STATE)
        except Exception:
            pass
            
        await page.wait_for_timeout(4000)
        print("Página carregada! URL:", page.url)
        
        # 1. Consultar lista de apps via API REST /api/v1/items
        data = await page.evaluate('''async () => {
            const resItems = await fetch('/api/v1/items?resourceType=app&limit=100');
            const items = await resItems.json();
            
            // Consultar detalhes do app Vendas Análise - Analítico (dcfc3ede-5eab-407c-a9ce-12b546eb5bdf)
            const appId = "dcfc3ede-5eab-407c-a9ce-12b546eb5bdf";
            let appDetail = null;
            try {
                const resApp = await fetch(`/api/v1/apps/${appId}`);
                appDetail = await resApp.json();
            } catch(e) {
                appDetail = { error: String(e) };
            }

            // Consultar histórico de reloads do app
            let reloads = null;
            try {
                const resReloads = await fetch(`/api/v1/reloads?appId=${appId}&limit=10`);
                reloads = await resReloads.json();
            } catch(e) {
                reloads = { error: String(e) };
            }

            // Consultar reload-tasks do app
            let tasks = null;
            try {
                const resTasks = await fetch(`/api/v1/reload-tasks?appId=${appId}`);
                tasks = await resTasks.json();
            } catch(e) {
                tasks = { error: String(e) };
            }

            return { items, appDetail, reloads, tasks };
        }''')
        
        await browser.close()
        return data

if __name__ == '__main__':
    res = asyncio.run(inspect_cloud())
    print("\n--- APPS DISPONÍVEIS NO QLIK CLOUD ---")
    items = res.get('items', {}).get('data', [])
    print(f"Total de apps encontrados: {len(items)}")
    for it in items:
        name = it.get('name', '')
        res_id = it.get('resourceId', '')
        updated = it.get('updatedAt', '')
        print(f"  📱 {name:40s} | ID: {res_id} | Atualizado: {updated}")
        
    print("\n--- DETALHES DO APP VENDAS ANÁLISE - ANALÍTICO ---")
    app_d = res.get('appDetail', {})
    print(f"Nome: {app_d.get('attributes', {}).get('name')}")
    print(f"Último reload (lastReloadTime): {app_d.get('attributes', {}).get('lastReloadTime')}")
    print(f"Modificado em (modifiedDate): {app_d.get('attributes', {}).get('modifiedDate')}")
    
    print("\n--- HISTÓRICO DE RELOADS DO APP NO CLOUD ---")
    reloads = res.get('reloads', {}).get('data', [])
    print(f"Histórico de reloads (últimos {len(reloads)}):")
    for r in reloads:
        status = r.get('status')
        endTime = r.get('endTime')
        duration = r.get('duration')
        log = r.get('log', '')
        print(f"  🔄 Status: {status:10s} | Fim: {endTime} | Duração: {duration}s")
        
    print("\n--- TAREFAS DE AGENDAMENTO (RELOAD TASKS) ---")
    tasks = res.get('tasks', {})
    print("Tasks:", json.dumps(tasks, indent=2))
