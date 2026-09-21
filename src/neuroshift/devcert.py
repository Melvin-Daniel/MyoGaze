"""Self-signed CA + server cert so iPhone Safari can trust the LAN HTTPS page."""

from __future__ import annotations

import datetime as dt
import ipaddress
import subprocess
from pathlib import Path


def cert_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "config" / "devcerts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ca_cer_path() -> Path:
    return cert_dir() / "ca.cer"


def ensure_dev_certs(lan_ips: list[str]) -> tuple[Path, Path] | None:
    """Return (server cert.pem, key.pem) or None if we could not mint a certificate."""
    folder = cert_dir()
    cert_path = folder / "cert.pem"
    key_path = folder / "key.pem"
    names = _san_names(lan_ips)
    minted = _mint_with_cryptography(cert_path, key_path, names) or _mint_with_openssl(
        cert_path, key_path, names
    )
    if minted or (cert_path.exists() and key_path.exists()):
        return cert_path, key_path
    return None


def _san_names(lan_ips: list[str]) -> list[str]:
    names = ["localhost", "127.0.0.1"]
    for ip in lan_ips:
        if ip and ip not in names:
            names.append(ip)
    return names


def _mint_with_cryptography(cert_path: Path, key_path: Path, names: list[str]) -> bool:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    except ImportError:
        return False

    folder = cert_path.parent
    now = dt.datetime.now(dt.timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "MyoGaze LAN CA")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    san: list[x509.GeneralName] = []
    for name in names:
        try:
            san.append(x509.IPAddress(ipaddress.ip_address(name)))
        except ValueError:
            san.append(x509.DNSName(name))

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "MyoGaze")])
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    encoding = serialization.Encoding
    folder.joinpath("ca.pem").write_bytes(ca_cert.public_bytes(encoding.PEM))
    folder.joinpath("ca.cer").write_bytes(ca_cert.public_bytes(encoding.DER))
    folder.joinpath("ca.key").write_bytes(
        ca_key.private_bytes(
            encoding=encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.write_bytes(
        server_key.private_bytes(
            encoding=encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(server_cert.public_bytes(encoding.PEM))
    return True


def _mint_with_openssl(cert_path: Path, key_path: Path, names: list[str]) -> bool:
    openssl = _which_openssl()
    if openssl is None:
        return False
    san = ",".join(f"IP:{n}" if _is_ip(n) else f"DNS:{n}" for n in names)
    try:
        subprocess.run(
            [
                openssl,
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key_path),
                "-out",
                str(cert_path),
                "-days",
                "825",
                "-nodes",
                "-subj",
                "/CN=MyoGaze",
                "-addext",
                f"subjectAltName={san}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return cert_path.exists() and key_path.exists()
    except (OSError, subprocess.CalledProcessError):
        return False


def _which_openssl() -> str | None:
    from shutil import which

    found = which("openssl")
    if found:
        return found
    git_openssl = Path(r"C:\Program Files\Git\usr\bin\openssl.exe")
    if git_openssl.exists():
        return str(git_openssl)
    return None


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
