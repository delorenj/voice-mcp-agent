#!/bin/bash
# 🔍 Quick SSL Certificate Status Checker

echo "🔍 SSL CERTIFICATE STATUS CHECK"
echo "==============================="
echo ""

domains=("lk.delo.sh" "lk-whip.delo.sh" "lk-turn.delo.sh")

for domain in "${domains[@]}"; do
    echo "🌐 Checking $domain:"
    
    # Check if domain responds
    if curl -s --connect-timeout 5 "https://$domain" &>/dev/null; then
        # Get certificate info
        cert_info=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -issuer -dates 2>/dev/null)
        
        if echo "$cert_info" | grep -q "Let's Encrypt"; then
            echo "  ✅ Let's Encrypt certificate ACTIVE"
            echo "  📅 $(echo "$cert_info" | grep "notAfter")"
        elif echo "$cert_info" | grep -q "self-signed\|localhost"; then
            echo "  ❌ Self-signed certificate (NEEDS FIX)"
        else
            echo "  ❓ Unknown certificate type"
        fi
    else
        echo "  🔌 Service not responding on HTTPS"
    fi
    echo ""
done

echo "🔧 Traefik logs (last 5 SSL-related lines):"
docker logs traefik 2>&1 | grep -i "certificate\|letsencrypt\|error" | tail -5
echo ""
echo "💡 To fix SSL issues, run: ./ULTIMATE-SSL-EMERGENCY-FIX.sh"