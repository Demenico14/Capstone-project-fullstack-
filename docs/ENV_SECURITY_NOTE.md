# Environment Variables Security Guide

## Important Security Notes

### Sentinel Hub Credentials

Your `.env.local` file contains sensitive API credentials. Here's what you need to know:

#### Client Secret Security

The `SENTINELHUB_CLIENT_SECRET` should **NEVER** have the `NEXT_PUBLIC_` prefix because:

1. **NEXT_PUBLIC_** variables are exposed to the browser (client-side)
2. Anyone can view them in the browser's developer tools
3. This allows unauthorized access to your Sentinel Hub account

#### Correct Configuration

\`\`\`bash
# ✅ CORRECT - Client ID can be public
NEXT_PUBLIC_SENTINELHUB_CLIENT_ID=bd616fb8-52b6-47e5-948e-45c4f4e07f29

# ✅ CORRECT - Client Secret is server-side only (no NEXT_PUBLIC_ prefix)
SENTINELHUB_CLIENT_SECRET=NBZJWMeJbLz8W8WMI3gojizeNHjku16k

# ✅ CORRECT - Instance ID can be public
NEXT_PUBLIC_SENTINEL_HUB_INSTANCE_ID=b29609d3-f80d-4370-84fd-431e6f285c84
\`\`\`

#### Wrong Configuration (Security Risk)

\`\`\`bash
# ❌ WRONG - Exposes secret to browser
NEXT_PUBLIC_SENTINELHUB_CLIENT_SECRET=NBZJWMeJbLz8W8WMI3gojizeNHjku16k
\`\`\`

### How It Works

1. The satellite imagery API route (`app/api/satellite/route.ts`) runs on the **server**
2. It can access both `NEXT_PUBLIC_*` and regular environment variables
3. The client secret is used server-side to authenticate with Sentinel Hub
4. The browser never sees the client secret

### After Updating .env.local

**You MUST restart your Next.js development server** for environment variable changes to take effect:

\`\`\`bash
# Stop the server (Ctrl+C)
# Then restart it
npm run dev
\`\`\`

### Git Security

Make sure `.env.local` is in your `.gitignore` file:

\`\`\`
# .gitignore
.env.local
.env*.local
\`\`\`

Never commit `.env.local` to version control!

### Production Deployment

When deploying to Vercel or other platforms:

1. Add environment variables through the platform's dashboard
2. Keep `SENTINELHUB_CLIENT_SECRET` as a regular environment variable (not public)
3. Only add `NEXT_PUBLIC_` prefix to variables that need to be accessible in the browser
