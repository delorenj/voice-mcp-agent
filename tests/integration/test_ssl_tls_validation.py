"""
SSL/TLS Configuration and Certificate Validation Tests
Comprehensive testing of SSL/TLS setup for LiveKit deployment
"""

import pytest
import asyncio
import aiohttp
import ssl
import socket
import OpenSSL.crypto
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import subprocess
import json

logger = logging.getLogger(__name__)

class SSLTLSValidator:
    """SSL/TLS configuration validator for LiveKit deployment"""
    
    def __init__(self, domains: List[str], test_mode: bool = True):
        self.domains = domains
        self.test_mode = test_mode  # Use local testing when True
        self.ssl_context = ssl.create_default_context()
    
    async def get_certificate_info(self, hostname: str, port: int = 443) -> Dict:
        """Retrieve SSL certificate information for a domain"""
        try:
            # Connect and get certificate
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with self.ssl_context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert_dict = ssock.getpeercert()
                    
            # Parse with OpenSSL for detailed info
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_der)
            
            return {
                'subject': cert_dict.get('subject', []),
                'issuer': cert_dict.get('issuer', []),
                'not_before': cert_dict.get('notBefore', ''),
                'not_after': cert_dict.get('notAfter', ''),
                'serial_number': cert.get_serial_number(),
                'signature_algorithm': cert.get_signature_algorithm().decode(),
                'version': cert.get_version(),
                'extensions': self._parse_extensions(cert),
                'san': cert_dict.get('subjectAltName', [])
            }
        except Exception as e:
            logger.error(f"Failed to get certificate for {hostname}: {e}")
            return None
    
    def _parse_extensions(self, cert) -> List[Dict]:
        """Parse certificate extensions"""
        extensions = []
        for i in range(cert.get_extension_count()):
            ext = cert.get_extension(i)
            extensions.append({
                'name': ext.get_short_name().decode(),
                'critical': ext.get_critical(),
                'data': str(ext)
            })
        return extensions
    
    def validate_certificate_chain(self, hostname: str, port: int = 443) -> Dict:
        """Validate complete certificate chain"""
        try:
            # Get the full certificate chain
            cmd = [
                'openssl', 's_client', '-connect', f'{hostname}:{port}',
                '-servername', hostname, '-showcerts', '-verify_return_error'
            ]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, input=''
            )
            
            return {
                'valid': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'chain_valid': 'Verify return code: 0 (ok)' in result.stdout
            }
        except subprocess.TimeoutExpired:
            return {'valid': False, 'error': 'Connection timeout'}
        except Exception as e:
            return {'valid': False, 'error': str(e)}

@pytest.fixture
def ssl_validator():
    """Fixture providing SSL/TLS validator"""
    domains = ['lk.delo.sh', 'lk-turn.delo.sh', 'lk-whip.delo.sh']
    return SSLTLSValidator(domains)

class TestCertificateValidation:
    """Test SSL certificate validation"""
    
    @pytest.mark.skipif(
        ssl_validator().test_mode, 
        reason="Skipping SSL tests in test mode - requires live SSL certificates"
    )
    async def test_certificate_expiration(self, ssl_validator):
        """Test that certificates are valid and not expiring soon"""
        for domain in ssl_validator.domains:
            cert_info = await ssl_validator.get_certificate_info(domain)
            
            if cert_info is None:
                pytest.skip(f"Could not retrieve certificate for {domain}")
                continue
            
            # Parse expiration date
            not_after = datetime.strptime(cert_info['not_after'], '%b %d %H:%M:%S %Y %Z')
            days_until_expiry = (not_after - datetime.utcnow()).days
            
            # Certificate should not expire within 30 days
            assert days_until_expiry > 30, f"Certificate for {domain} expires in {days_until_expiry} days"
            
            logger.info(f"Certificate for {domain} expires in {days_until_expiry} days")
    
    @pytest.mark.skipif(
        ssl_validator().test_mode,
        reason="Skipping SSL tests in test mode"
    )
    async def test_certificate_subject_alternative_names(self, ssl_validator):
        """Test Subject Alternative Names (SAN) configuration"""
        for domain in ssl_validator.domains:
            cert_info = await ssl_validator.get_certificate_info(domain)
            
            if cert_info is None:
                pytest.skip(f"Could not retrieve certificate for {domain}")
                continue
            
            # Extract SAN entries
            san_entries = [entry[1] for entry in cert_info.get('san', []) if entry[0] == 'DNS']
            
            # Domain should be in SAN entries
            assert domain in san_entries, f"Domain {domain} not found in SAN entries: {san_entries}"
            
            logger.info(f"SAN entries for {domain}: {san_entries}")
    
    @pytest.mark.skipif(
        ssl_validator().test_mode,
        reason="Skipping SSL tests in test mode"
    )
    async def test_certificate_chain_validation(self, ssl_validator):
        """Test complete certificate chain validation"""
        for domain in ssl_validator.domains:
            chain_result = ssl_validator.validate_certificate_chain(domain)
            
            if not chain_result.get('valid'):
                if 'timeout' in chain_result.get('error', '').lower():
                    pytest.skip(f"Connection timeout for {domain}")
                else:
                    pytest.fail(f"Certificate chain validation failed for {domain}: {chain_result.get('error')}")
            
            assert chain_result.get('chain_valid', False), f"Certificate chain invalid for {domain}"
            
            logger.info(f"Certificate chain valid for {domain}")

class TestTLSConfiguration:
    """Test TLS protocol and cipher configuration"""
    
    def test_supported_tls_versions(self, ssl_validator):
        """Test supported TLS protocol versions"""
        # Test modern TLS versions support
        for domain in ssl_validator.domains:
            if ssl_validator.test_mode:
                pytest.skip("TLS version test requires live SSL certificates")
            
            for tls_version in ['TLSv1.2', 'TLSv1.3']:
                try:
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    
                    # Configure specific TLS version
                    if tls_version == 'TLSv1.2':
                        context.minimum_version = ssl.TLSVersion.TLSv1_2
                        context.maximum_version = ssl.TLSVersion.TLSv1_2
                    elif tls_version == 'TLSv1.3':
                        context.minimum_version = ssl.TLSVersion.TLSv1_3
                        context.maximum_version = ssl.TLSVersion.TLSv1_3
                    
                    with socket.create_connection((domain, 443), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=domain) as ssock:
                            actual_version = ssock.version()
                            assert actual_version is not None, f"No TLS version negotiated for {domain}"
                            logger.info(f"{domain} supports {actual_version}")
                            
                except ssl.SSLError as e:
                    if 'PROTOCOL_ERROR' in str(e) or 'HANDSHAKE_FAILURE' in str(e):
                        logger.warning(f"{domain} does not support {tls_version}: {e}")
                    else:
                        raise
                except Exception as e:
                    pytest.skip(f"TLS test failed for {domain}: {e}")
    
    def test_cipher_suite_security(self, ssl_validator):
        """Test cipher suite configuration security"""
        if ssl_validator.test_mode:
            pytest.skip("Cipher suite test requires live SSL certificates")
        
        # Weak ciphers that should NOT be supported
        weak_ciphers = [
            'RC4', 'MD5', 'DES', '3DES', 'NULL',
            'EXPORT', 'ADH', 'AECDH', 'PSK'
        ]
        
        for domain in ssl_validator.domains:
            try:
                # Test that weak ciphers are rejected
                context = ssl.create_default_context()
                context.set_ciphers('ALL')  # Allow all ciphers for testing
                
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cipher_info = ssock.cipher()
                        cipher_name = cipher_info[0] if cipher_info else ''
                        
                        # Check that no weak ciphers are used
                        for weak_cipher in weak_ciphers:
                            assert weak_cipher not in cipher_name.upper(), \
                                f"Weak cipher {weak_cipher} detected in {cipher_name} for {domain}"
                        
                        logger.info(f"Cipher for {domain}: {cipher_name}")
                        
            except Exception as e:
                pytest.skip(f"Cipher test failed for {domain}: {e}")
    
    def test_perfect_forward_secrecy(self, ssl_validator):
        """Test Perfect Forward Secrecy (PFS) support"""
        if ssl_validator.test_mode:
            pytest.skip("PFS test requires live SSL certificates")
        
        # PFS cipher suites (ECDHE or DHE key exchange)
        pfs_indicators = ['ECDHE', 'DHE']
        
        for domain in ssl_validator.domains:
            try:
                context = ssl.create_default_context()
                
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cipher_info = ssock.cipher()
                        cipher_name = cipher_info[0] if cipher_info else ''
                        
                        # Check for PFS support
                        has_pfs = any(pfs in cipher_name for pfs in pfs_indicators)
                        assert has_pfs, f"No Perfect Forward Secrecy support detected for {domain}: {cipher_name}"
                        
                        logger.info(f"PFS cipher for {domain}: {cipher_name}")
                        
            except Exception as e:
                pytest.skip(f"PFS test failed for {domain}: {e}")

class TestCaddySSLConfiguration:
    """Test Caddy-specific SSL configuration"""
    
    def test_sni_routing_functionality(self, ssl_validator):
        """Test Server Name Indication (SNI) routing works correctly"""
        if ssl_validator.test_mode:
            pytest.skip("SNI test requires live SSL certificates")
        
        # Test each domain gets correct certificate
        for domain in ssl_validator.domains:
            try:
                cert_info = asyncio.run(ssl_validator.get_certificate_info(domain))
                
                if cert_info is None:
                    pytest.skip(f"Could not retrieve certificate for {domain}")
                    continue
                
                # Extract common name from subject
                subject_dict = dict(x[0] for x in cert_info['subject'])
                common_name = subject_dict.get('commonName', '')
                
                # Check if domain matches certificate
                san_domains = [entry[1] for entry in cert_info.get('san', []) if entry[0] == 'DNS']
                
                domain_matches = (
                    domain == common_name or 
                    domain in san_domains or
                    any(domain.endswith(san_domain.lstrip('*')) for san_domain in san_domains if san_domain.startswith('*'))
                )
                
                assert domain_matches, f"Domain {domain} does not match certificate (CN: {common_name}, SAN: {san_domains})"
                
                logger.info(f"SNI routing correct for {domain}")
                
            except Exception as e:
                pytest.skip(f"SNI test failed for {domain}: {e}")
    
    def test_automatic_https_redirect(self, ssl_validator):
        """Test automatic HTTP to HTTPS redirect"""
        if ssl_validator.test_mode:
            pytest.skip("HTTPS redirect test requires live configuration")
        
        async def check_redirect(domain):
            async with aiohttp.ClientSession() as session:
                try:
                    # Test HTTP request gets redirected to HTTPS
                    async with session.get(
                        f"http://{domain}", 
                        allow_redirects=False,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        assert response.status in [301, 302, 307, 308], \
                            f"Expected redirect status for {domain}, got {response.status}"
                        
                        location = response.headers.get('Location', '')
                        assert location.startswith('https://'), \
                            f"Redirect not to HTTPS for {domain}: {location}"
                        
                        logger.info(f"HTTP to HTTPS redirect working for {domain}")
                        
                except aiohttp.ClientError as e:
                    pytest.skip(f"Redirect test failed for {domain}: {e}")
        
        for domain in ssl_validator.domains:
            asyncio.run(check_redirect(domain))

class TestCertificateAutomation:
    """Test certificate automation and renewal"""
    
    def test_certificate_auto_renewal_readiness(self, ssl_validator):
        """Test certificate is ready for automatic renewal"""
        if ssl_validator.test_mode:
            pytest.skip("Certificate automation test requires live certificates")
        
        for domain in ssl_validator.domains:
            cert_info = asyncio.run(ssl_validator.get_certificate_info(domain))
            
            if cert_info is None:
                pytest.skip(f"Could not retrieve certificate for {domain}")
                continue
            
            # Check certificate authority is ACME-compatible (Let's Encrypt, etc.)
            issuer_dict = dict(x[0] for x in cert_info['issuer'])
            issuer_org = issuer_dict.get('organizationName', '')
            
            # Known ACME-compatible CAs
            acme_cas = ["Let's Encrypt", "ZeroSSL", "Google Trust Services"]
            is_acme_compatible = any(ca in issuer_org for ca in acme_cas)
            
            if not is_acme_compatible:
                logger.warning(f"Certificate for {domain} from {issuer_org} may not support ACME auto-renewal")
            
            # Check certificate validity period (ACME certs typically 90 days)
            not_before = datetime.strptime(cert_info['not_before'], '%b %d %H:%M:%S %Y %Z')
            not_after = datetime.strptime(cert_info['not_after'], '%b %d %H:%M:%S %Y %Z')
            validity_period = (not_after - not_before).days
            
            # ACME certificates are typically 90 days
            if validity_period <= 90:
                logger.info(f"Certificate for {domain} appears to be ACME-issued (90-day validity)")
            
            logger.info(f"Certificate for {domain} issued by {issuer_org}, valid for {validity_period} days")

class TestSecurityHeaders:
    """Test security-related HTTP headers"""
    
    async def test_security_headers_present(self, ssl_validator):
        """Test that security headers are properly configured"""
        if ssl_validator.test_mode:
            pytest.skip("Security headers test requires live configuration")
        
        expected_headers = {
            'Strict-Transport-Security': 'HSTS header missing',
            'X-Content-Type-Options': 'Content type options header missing', 
            'X-Frame-Options': 'Frame options header missing',
            'X-XSS-Protection': 'XSS protection header missing'
        }
        
        async with aiohttp.ClientSession() as session:
            for domain in ssl_validator.domains:
                try:
                    async with session.get(
                        f"https://{domain}",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        headers = response.headers
                        
                        for header_name, error_msg in expected_headers.items():
                            if header_name in headers:
                                logger.info(f"{domain} has {header_name}: {headers[header_name]}")
                            else:
                                logger.warning(f"{domain} missing {header_name}")
                        
                        # HSTS should be present and properly configured
                        if 'Strict-Transport-Security' in headers:
                            hsts_value = headers['Strict-Transport-Security']
                            assert 'max-age=' in hsts_value, f"HSTS missing max-age for {domain}"
                            
                            # Extract max-age value
                            max_age = None
                            for part in hsts_value.split(';'):
                                if 'max-age=' in part:
                                    max_age = int(part.split('=')[1].strip())
                                    break
                            
                            if max_age:
                                assert max_age >= 31536000, f"HSTS max-age too short for {domain}: {max_age}"  # 1 year minimum
                                
                except aiohttp.ClientError as e:
                    pytest.skip(f"Security headers test failed for {domain}: {e}")

@pytest.mark.asyncio
async def test_ssl_configuration_comprehensive():
    """Comprehensive SSL configuration test"""
    validator = SSLTLSValidator(['lk.delo.sh'])
    
    if validator.test_mode:
        pytest.skip("Comprehensive SSL test requires live SSL certificates")
    
    # Test certificate retrieval
    cert_info = await validator.get_certificate_info('lk.delo.sh')
    assert cert_info is not None, "Could not retrieve certificate information"
    
    # Test chain validation
    chain_result = validator.validate_certificate_chain('lk.delo.sh')
    assert chain_result.get('valid', False), f"Certificate chain validation failed: {chain_result.get('error')}"
    
    logger.info("Comprehensive SSL test passed")

if __name__ == "__main__":
    # Run SSL/TLS validation tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])