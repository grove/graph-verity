// Additional real-Chrome checks, sharing the established saved-fixture journey.
import assert from 'node:assert/strict';

export async function check({send, evaluate, until, click, review, confirms}) {
  const forward = 'Which official websites does the University of Tromsø list?';
  const date = 'When was the University of Tromsø founded?';
  await send('Emulation.setDeviceMetricsOverride', {width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await review(date, 'en', '/entity/Q279724');
  await click('approve');
  await until("!document.getElementById('results').hidden");
  assert.match(await evaluate("document.getElementById('answers').textContent"), /dateTime/);
  assert.match(await evaluate("document.getElementById('answers').textContent"), /1968-01-01T00:00:00Z/);

  await review(forward, 'en', '/entity/Q279724');
  const token = await evaluate('approval.token');
  await click('approve');
  await until("!document.getElementById('results').hidden");
  // Debugger invokes the public authenticated client, bypassing only disabled UI.
  const redeem = t => evaluate(`api('/api/nl-ask-v2/confirm', {token:${JSON.stringify(t)},decision:'approve'}).then(()=>true,()=>false)`);
  assert.equal(await redeem(token), false, 'replayed approval must fail at the server');

  await review(forward, 'en', '/entity/Q279724');
  const stale = await evaluate('approval.token');
  await click('edit');
  await until("document.getElementById('review').hidden");
  // Wait for the actual cancellation request, preserving its ordering before redemption.
  await evaluate("api('/api/nl-ask-v2/cancel', {})");
  assert.equal(await redeem(stale), false);

  await review(forward, 'en', '/entity/Q279724');
  const expires = await evaluate('approval.token');
  // The Python test uses a two-second review lease in this isolated server.
  await until("document.getElementById('status').textContent.includes('Review expired')");
  assert.ok(await evaluate("document.getElementById('approve').disabled && document.getElementById('results').hidden"));
  assert.equal(await redeem(expires), false);

  await review(forward, 'en', '/entity/Q279724');
  const before = confirms();
  await evaluate(`window.alphaFetch = window.fetch; window.fetch = (...args) => {
    if (args[0].endsWith('/confirm')) return Promise.reject(new TypeError('Synthetic network failure; no answer is asserted'));
    return window.alphaFetch(...args); };`);
  await click('approve');
  await until("document.getElementById('status').textContent.includes('Synthetic network failure')");
  assert.equal(confirms(), before);
  assert.ok(await evaluate("document.getElementById('results').hidden && document.getElementById('approve').disabled"));
  await evaluate('window.fetch = window.alphaFetch');

  if (process.env.ASK_ALPHA_CLIPPED_URL) {
    await send('Page.navigate', {url:process.env.ASK_ALPHA_CLIPPED_URL});
    await until(`location.origin === ${JSON.stringify(new URL(process.env.ASK_ALPHA_CLIPPED_URL).origin)} && document.getElementById('ask') && !document.getElementById('ask').disabled`);
    await review(forward, 'en', '/entity/Q279724');
    await click('approve');
    await until("!document.getElementById('results').hidden");
    assert.match(await evaluate("document.getElementById('result-status').textContent"), /Rows truncated; evidence complete/);
    const receipt = await evaluate("JSON.parse(document.getElementById('receipt').textContent)");
    assert.equal(receipt.provenance.proposal_origin, 'saved_draft_demo');
    assert.equal(receipt.answers.length, 1);
    assert.equal(receipt.outcome.result.complete_within_scope, false);
    assert.equal(receipt.outcome.result.evidence_complete_for_returned_rows, true);
    await review('Hvilke offisielle navn har Universitetet i Tromsø?', 'nb', '/entity/Q279724');
    await click('approve');
    await until("!document.getElementById('results').hidden");
    assert.match(await evaluate("document.getElementById('result-status').textContent"), /Rows complete; evidence truncated/);
    assert.match(await evaluate("document.getElementById('answers').textContent"), /Original source witness was clipped/);
  }
  assert.equal(await evaluate("document.querySelectorAll('img,iframe,object,script:not([src])').length"), 0);
  console.log('Ask alpha: typed date, server replay/edit/expiry rejection, transport failure, and real Rust row/evidence clipping passed');
}
