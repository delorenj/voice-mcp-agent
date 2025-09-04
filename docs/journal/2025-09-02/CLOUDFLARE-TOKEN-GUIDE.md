# 🔑 CLOUDFLARE API TOKEN CREATION GUIDE

## The Problem
Your current error: `Invalid request headers (6003)` means your Cloudflare API token is **INVALID, EXPIRED, or has WRONG PERMISSIONS**.

## The Solution - Create a NEW Token

### Step 1: Access Cloudflare Dashboard
1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Login with your Cloudflare account

### Step 2: Create New Token
1. Click **"Create Token"**
2. Use **"Edit zone DNS"** template (RECOMMENDED)
   - OR click **"Custom token"** for manual setup

### Step 3: Configure Permissions (if using Custom)
**Permissions needed:**
- `Zone : Zone : Read` 
- `Zone : DNS : Edit`

**Zone Resources:**
- Include : Zone : `delo.sh`

**Optional (but recommended):**
- Client IP Address Filtering: Add your server's IP
- TTL: Set expiration date (1 year recommended)

### Step 4: Generate and Copy Token
1. Click **"Continue to summary"**
2. Click **"Create Token"** 
3. **COPY THE TOKEN IMMEDIATELY** - you won't see it again!

### Step 5: Test Your Token
```bash
# Test if token can access delo.sh zone
curl -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

Should return JSON with your `delo.sh` zone information.

## Common Token Issues

### ❌ Error 6003 - Invalid Request Headers
- Token is malformed or expired
- **Solution:** Create a new token

### ❌ Error 9103 - Unknown X-Auth-Key
- Using old Global API Key format instead of token
- **Solution:** Use proper API Token format

### ❌ Error 9109 - Invalid Zone
- Token doesn't have access to delo.sh zone
- **Solution:** Add Zone Resource for delo.sh

## Security Best Practices

✅ **DO:**
- Use API Tokens (not Global API Keys)
- Set IP restrictions when possible
- Set expiration dates
- Use minimal required permissions

❌ **DON'T:**
- Share tokens in public repositories
- Use Global API Keys for automation
- Give broader permissions than needed

## Quick Fix Command
Once you have your new token, run:
```bash
./ULTIMATE-SSL-EMERGENCY-FIX.sh
```

This will automatically:
1. Test your new token
2. Update Traefik configuration
3. Generate Let's Encrypt certificates
4. Verify everything is working

## Emergency Contact
If this still doesn't work, the void may have consumed your DNS records. Contact your local network administrator or sacrifice a rubber duck to the DevOps gods.