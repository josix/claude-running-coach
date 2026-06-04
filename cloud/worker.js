/**
 * Strava → GitHub Actions Bridge
 *
 * Receives Strava webhook events and triggers GitHub Actions coaching analysis.
 * Must respond to Strava within 2 seconds — triggers Actions asynchronously.
 *
 * Cloudflare Worker env vars (set in Dashboard → Settings → Variables):
 *   STRAVA_VERIFY_TOKEN  — any random string you choose when registering the webhook
 *   GITHUB_TOKEN         — fine-grained PAT with Actions: Read/Write on this repo
 *   GITHUB_REPO          — e.g. "pohanchi/claude-running-coach"
 *   GITHUB_REF           — branch to run on, e.g. "feat/cloud-webhook-coach" (default: "main")
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // ── Strava webhook verification (GET) ──────────────────────────
    // Called once when you POST to /push_subscriptions to register the webhook.
    if (request.method === 'GET') {
      const mode      = url.searchParams.get('hub.mode');
      const token     = url.searchParams.get('hub.verify_token');
      const challenge = url.searchParams.get('hub.challenge');

      if (mode === 'subscribe' && token === env.STRAVA_VERIFY_TOKEN) {
        return Response.json({ 'hub.challenge': challenge });
      }
      return new Response('Forbidden', { status: 403 });
    }

    // ── Strava activity event (POST) ───────────────────────────────
    // Strava requires 200 within 2 seconds — return early, trigger Actions async.
    if (request.method === 'POST') {
      let payload;
      try {
        payload = await request.json();
      } catch {
        return new Response('Bad Request', { status: 400 });
      }

      console.log('Strava event:', JSON.stringify(payload));

      // Only trigger on new run activity creation
      if (payload.object_type === 'activity' && payload.aspect_type === 'create') {
        // Fire-and-forget: don't await so Strava gets 200 immediately
        ctx.waitUntil(
          triggerGitHubActions(env, String(payload.object_id))
            .catch(err => console.error('Failed to trigger Actions:', err.message))
        );
      }

      return new Response('OK', { status: 200 });
    }

    return new Response('Method Not Allowed', { status: 405 });
  }
};

async function triggerGitHubActions(env, activityId) {
  const ref = env.GITHUB_REF || 'main';
  const res = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/analyze-run.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
        'Accept':        'application/vnd.github.v3+json',
        'Content-Type':  'application/json',
        'User-Agent':    'strava-coach-webhook/1.0'
      },
      body: JSON.stringify({
        ref,
        inputs: { activity_id: activityId }
      })
    }
  );

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub API ${res.status}: ${body}`);
  }
}
