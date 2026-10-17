import assert from "node:assert/strict";
export default async function ({ send, evaluate, until, key, requests, exceptions, url }) {
  await until("document.getElementById('controls') && !document.getElementById('controls').disabled");
  assert.equal(await evaluate("location.hash"), "");
  const tree = await send("Accessibility.getFullAXTree");
  for (const name of ["Role", "Snapshot", "Graph", "Task / query", "Top k"]) {
    assert(tree.nodes.some(n => n.role?.value === "combobox" && n.name?.value === name), name);
  }
  await evaluate("document.getElementById('task').focus()");
  await key("Tab", "Tab", 9);
  assert.equal(await evaluate("document.activeElement.id"), "limit");
  await evaluate("document.getElementById('selection').requestSubmit()");
  await until("!document.getElementById('review').hidden");
  assert.equal(await evaluate("document.getElementById('query') === document.activeElement"), true);
  assert.equal(await evaluate("document.getElementById('reveal').textContent"), "");
  assert.equal(await evaluate("document.querySelectorAll('#lists section').length"), 2);
  assert.equal(await evaluate("document.querySelector('#lists img')"), null);
  assert.equal(await evaluate("document.body.textContent.includes('PRIVATE_')"), false, await evaluate("document.body.textContent.match(/.{0,60}PRIVATE_.{0,100}/)?.[0]"));
  assert.equal(await evaluate("document.getElementById('lists').textContent.includes('onerror')"), true);
  assert.equal(await evaluate("window.injected"), undefined);
  await evaluate(`document.querySelectorAll('#ratings select').forEach(s => s.value='irrelevant');
    document.querySelectorAll('#rubric select').forEach(s => s.value=s.id.endsWith('confidence')?'4':'uncertain');
    document.getElementById('universe').checked=true; document.getElementById('no-match').checked=true;
    document.getElementById('preference').value='tie'; document.getElementById('judgments').requestSubmit()`);
  await until("document.getElementById('reveal').textContent.includes('bm25')");
  assert.equal(await evaluate("document.getElementById('submit').disabled"), true);
  assert.equal(await evaluate("document.getElementById('reveal').textContent.includes('selective')"), true);
  await evaluate(`document.getElementById('task').selectedIndex=1; document.getElementById('selection').requestSubmit()`);
  await until("!document.getElementById('review').hidden || document.getElementById('status').textContent.includes('unavailable')");
  assert.equal(await evaluate("document.getElementById('review').hidden"), false, await evaluate("document.getElementById('status').textContent"));
  assert.equal(await evaluate("document.getElementById('reveal').textContent"), "");
  assert.equal(await evaluate("document.getElementById('preference').disabled"), false);
  assert.equal(await evaluate("document.getElementById('universe').checked"), false);
  assert(requests.every(request => new URL(request).origin === new URL(url).origin), "No external page requests");
  assert.deepEqual(exceptions, []);
  await send("Emulation.setScriptExecutionDisabled", { value: true });
  await send("Page.navigate", { url: new URL(url).origin + "/" });
  await until("document.querySelector('noscript') && document.getElementById('controls').disabled");
  assert.match(await evaluate("document.querySelector('noscript').textContent"), /No review has been recorded/);
  console.log("Headless hybrid review: blinding, inert source text, judgment/reveal, keyboard/AX and offline checks passed");
}
