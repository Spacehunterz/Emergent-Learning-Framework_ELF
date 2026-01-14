const ALLOWED_ORIGINS = [
  'http://localhost:3001',
  'http://localhost:8888',
  'https://spacehunterz.github.io'
];

function corsHeaders(origin) {
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders(origin) });
    }

    const url = new URL(request.url);

    if (url.pathname === '/oauth/config' && request.method === 'GET') {
      return new Response(JSON.stringify({
        client_id: env.GITHUB_CLIENT_ID,
        redirect_uri: env.OAUTH_REDIRECT_URI || 'http://localhost:8888/api/auth/callback'
      }), {
        headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
      });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
      });
    }

    if (url.pathname === '/oauth/token') {
      return handleTokenExchange(request, env, origin);
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
    });
  }
};

async function handleTokenExchange(request, env, origin) {
  try {
    const body = await request.json();
    const { code, redirect_uri } = body;

    if (!code) {
      return new Response(JSON.stringify({ error: 'Missing code parameter' }), {
        status: 400,
        headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
      });
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
      return new Response(JSON.stringify({
        error: tokenData.error,
        error_description: tokenData.error_description
      }), {
        status: 400,
        headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      access_token: tokenData.access_token,
      token_type: tokenData.token_type,
      scope: tokenData.scope
    }), {
      headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: 'Token exchange failed' }), {
      status: 500,
      headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
    });
  }
}
