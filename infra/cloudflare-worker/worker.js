const ALLOWED_ORIGINS = [
  'http://localhost:3001',
  'http://localhost:8888',
  'https://spacehunterz.github.io'
];

function corsHeaders(origin) {
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Credentials': 'true',
  };
}

function jsonResponse(data, status = 200, origin = '') {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
  });
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders(origin) });
    }

    const url = new URL(request.url);

    if (url.pathname === '/oauth/config' && request.method === 'GET') {
      return jsonResponse({
        client_id: env.GITHUB_CLIENT_ID,
        redirect_uri: env.OAUTH_REDIRECT_URI || 'http://localhost:8888/api/auth/callback'
      }, 200, origin);
    }

    if (url.pathname === '/oauth/token' && request.method === 'POST') {
      return handleTokenExchange(request, env, origin);
    }

    if (url.pathname === '/leaderboard' && request.method === 'GET') {
      return handleGetLeaderboard(request, env, origin);
    }

    if (url.pathname === '/leaderboard/sync' && request.method === 'POST') {
      return handleSyncScore(request, env, origin);
    }

    return jsonResponse({ error: 'Not found' }, 404, origin);
  }
};

async function handleTokenExchange(request, env, origin) {
  try {
    const body = await request.json();
    const { code, redirect_uri } = body;

    if (!code) {
      return jsonResponse({ error: 'Missing code parameter' }, 400, origin);
    }

    const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: env.GITHUB_CLIENT_ID,
        client_secret: env.GITHUB_CLIENT_SECRET,
        code: code,
        redirect_uri: redirect_uri || env.OAUTH_REDIRECT_URI
      })
    });

    const tokenData = await tokenResponse.json();

    if (tokenData.error) {
      return jsonResponse({
        error: tokenData.error,
        error_description: tokenData.error_description
      }, 400, origin);
    }

    return jsonResponse({
      access_token: tokenData.access_token,
      token_type: tokenData.token_type,
      scope: tokenData.scope
    }, 200, origin);

  } catch (error) {
    return jsonResponse({ error: 'Token exchange failed' }, 500, origin);
  }
}

async function handleGetLeaderboard(request, env, origin) {
  try {
    const url = new URL(request.url);
    const limit = Math.min(parseInt(url.searchParams.get('limit') || '10'), 100);
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const result = await env.DB.prepare(`
      SELECT github_id, username, avatar_url, score,
             DENSE_RANK() OVER (ORDER BY score DESC) as rank
      FROM players
      WHERE score > 0
      ORDER BY score DESC
      LIMIT ? OFFSET ?
    `).bind(limit, offset).all();

    const countResult = await env.DB.prepare(
      'SELECT COUNT(*) as total FROM players WHERE score > 0'
    ).first();

    return jsonResponse({
      entries: result.results.map(row => ({
        rank: row.rank,
        github_id: row.github_id,
        username: row.username,
        avatar_url: row.avatar_url,
        score: row.score
      })),
      total_players: countResult?.total || 0,
      has_more: (offset + limit) < (countResult?.total || 0)
    }, 200, origin);

  } catch (error) {
    return jsonResponse({ error: 'Failed to fetch leaderboard', details: error.message }, 500, origin);
  }
}

async function handleSyncScore(request, env, origin) {
  try {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return jsonResponse({ error: 'Missing authorization' }, 401, origin);
    }

    const accessToken = authHeader.substring(7);

    const userResponse = await fetch('https://api.github.com/user', {
      headers: {
        'Authorization': `token ${accessToken}`,
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'ELF-Leaderboard'
      }
    });

    if (!userResponse.ok) {
      return jsonResponse({ error: 'Invalid token' }, 401, origin);
    }

    const userData = await userResponse.json();
    const body = await request.json();
    const { score } = body;

    if (typeof score !== 'number' || score < 0) {
      return jsonResponse({ error: 'Invalid score' }, 400, origin);
    }

    const existing = await env.DB.prepare(
      'SELECT score FROM players WHERE github_id = ?'
    ).bind(userData.id).first();

    if (existing) {
      if (score > existing.score) {
        await env.DB.prepare(`
          UPDATE players SET score = ?, username = ?, avatar_url = ?, updated_at = datetime('now')
          WHERE github_id = ?
        `).bind(score, userData.login, userData.avatar_url, userData.id).run();
      }
    } else {
      await env.DB.prepare(`
        INSERT INTO players (github_id, username, avatar_url, score)
        VALUES (?, ?, ?, ?)
      `).bind(userData.id, userData.login, userData.avatar_url, score).run();
    }

    const rankResult = await env.DB.prepare(`
      SELECT COUNT(*) + 1 as rank FROM players WHERE score > ?
    `).bind(score).first();

    return jsonResponse({
      success: true,
      score: score,
      rank: rankResult?.rank || 1,
      username: userData.login
    }, 200, origin);

  } catch (error) {
    return jsonResponse({ error: 'Sync failed', details: error.message }, 500, origin);
  }
}
