// Captura con navegador para páginas que cargan con JavaScript.
// Uso: node scripts/captura.cjs <url> <salida.html> <salida.png>
// Imprime JSON con el estado HTTP y la URL final. No evade CAPTCHAs ni bloqueos:
// si la página los muestra, la captura los registra tal cual.
const { chromium } = require("playwright");

(async () => {
  const [url, html, png] = process.argv.slice(2);
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ userAgent: "due-dilligent/0.1 (hackaton UNI; solo lectura)" });
    const resp = await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
    await page.waitForTimeout(1500);
    require("fs").writeFileSync(html, await page.content());
    await page.screenshot({ path: png, fullPage: true });
    console.log(JSON.stringify({ estado: resp ? resp.status() : null, url_final: page.url() }));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(String(e));
  process.exit(1);
});
