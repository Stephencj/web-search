"""Network service - handles IP detection and network access URLs."""

import base64
import io
import socket
from typing import Optional

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting


# Settings keys
EXTERNAL_URL_MODE_KEY = "external_url_mode"
MANUAL_EXTERNAL_URL_KEY = "manual_external_url"

# App port (should match Docker/deployment config)
APP_PORT = 8000


class NetworkService:
    """Service for network access management."""

    # Cache for IP detection (to avoid repeated API calls)
    _cached_external_ip: Optional[str] = None
    _cached_local_ip: Optional[str] = None

    def get_local_ip(self) -> str:
        """
        Get the local network IP address.

        Returns the LAN IP (e.g., 192.168.x.x) that other devices
        on the same network can use to access this machine.
        """
        if self._cached_local_ip:
            return self._cached_local_ip

        try:
            # Create a UDP socket and connect to an external address
            # This doesn't actually send data, but helps determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                # Connect to Google's DNS - doesn't actually send packets
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()

            self._cached_local_ip = ip
            return ip

        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            # Fallback methods
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                if ip.startswith("127."):
                    # localhost, try another method
                    raise ValueError("Got localhost")
                self._cached_local_ip = ip
                return ip
            except Exception:
                return "127.0.0.1"

    async def get_external_ip(self) -> Optional[str]:
        """
        Get the external/public IP address using ipify.org.

        Returns None if detection fails.
        """
        if self._cached_external_ip:
            return self._cached_external_ip

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://api.ipify.org?format=json")
                if response.status_code == 200:
                    data = response.json()
                    ip = data.get("ip")
                    if ip:
                        self._cached_external_ip = ip
                        return ip
        except Exception as e:
            logger.warning(f"Could not determine external IP: {e}")

        return None

    def clear_ip_cache(self) -> None:
        """Clear cached IP addresses."""
        self._cached_external_ip = None
        self._cached_local_ip = None

    async def get_external_url_mode(self, db: AsyncSession) -> str:
        """Get external URL mode: 'auto', 'manual', or 'disabled'."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == EXTERNAL_URL_MODE_KEY)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value.get("mode", "disabled")
        return "disabled"

    async def set_external_url_mode(self, db: AsyncSession, mode: str) -> None:
        """Set external URL mode."""
        if mode not in ("auto", "manual", "disabled"):
            raise ValueError("Mode must be 'auto', 'manual', or 'disabled'")

        result = await db.execute(
            select(AppSetting).where(AppSetting.key == EXTERNAL_URL_MODE_KEY)
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = {"mode": mode}
        else:
            setting = AppSetting(key=EXTERNAL_URL_MODE_KEY, value={"mode": mode})
            db.add(setting)

        await db.commit()

    async def get_manual_external_url(self, db: AsyncSession) -> Optional[str]:
        """Get manually configured external URL."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == MANUAL_EXTERNAL_URL_KEY)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value.get("url")
        return None

    async def set_manual_external_url(self, db: AsyncSession, url: Optional[str]) -> None:
        """Set manual external URL."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == MANUAL_EXTERNAL_URL_KEY)
        )
        setting = result.scalar_one_or_none()

        if url:
            # Ensure URL has protocol
            if not url.startswith(("http://", "https://")):
                url = f"http://{url}"
            # Remove trailing slash
            url = url.rstrip("/")

            if setting:
                setting.value = {"url": url}
            else:
                setting = AppSetting(key=MANUAL_EXTERNAL_URL_KEY, value={"url": url})
                db.add(setting)
        else:
            if setting:
                await db.delete(setting)

        await db.commit()

    async def get_access_urls(self, db: AsyncSession) -> dict:
        """
        Get all access URLs for the application.

        Returns dict with:
        - local_url: URL for same-network access
        - external_url: URL for internet access (if configured)
        - external_ip: Detected external IP (if auto mode)
        """
        local_ip = self.get_local_ip()
        local_url = f"http://{local_ip}:{APP_PORT}"

        result = {
            "local_ip": local_ip,
            "local_url": local_url,
            "external_url": None,
            "external_ip": None,
            "external_mode": await self.get_external_url_mode(db),
        }

        mode = result["external_mode"]

        if mode == "auto":
            external_ip = await self.get_external_ip()
            if external_ip:
                result["external_ip"] = external_ip
                result["external_url"] = f"http://{external_ip}:{APP_PORT}"

        elif mode == "manual":
            manual_url = await self.get_manual_external_url(db)
            if manual_url:
                result["external_url"] = manual_url

        return result

    async def test_external_access(self, url: str) -> dict:
        """
        Test if external URL is accessible.

        Returns dict with success status and details.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/api/health", follow_redirects=True)
                success = response.status_code == 200
                return {
                    "success": success,
                    "status_code": response.status_code,
                    "message": "External access working" if success else f"Got status {response.status_code}",
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "status_code": None,
                "message": "Connection timed out. Check port forwarding.",
            }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "status_code": None,
                "message": f"Could not connect: {str(e)[:100]}",
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "message": f"Error: {str(e)[:100]}",
            }

    def generate_qr_code_data(self, url: str) -> Optional[str]:
        """
        Generate QR code as base64 PNG data.

        Returns base64-encoded PNG string or None if generation fails.
        """
        try:
            import qrcode
            from qrcode.image.pure import PyPNGImage

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(image_factory=PyPNGImage)

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer)
            buffer.seek(0)
            b64_data = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{b64_data}"

        except ImportError:
            logger.warning("qrcode package not installed - QR code generation unavailable")
            return None
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            return None

    def get_port_forwarding_instructions(self) -> dict:
        """Get port forwarding setup instructions."""
        local_ip = self.get_local_ip()
        return {
            "title": "Port Forwarding Setup",
            "steps": [
                f"1. Access your router's admin panel (usually at http://192.168.1.1 or http://192.168.0.1)",
                "2. Look for 'Port Forwarding', 'Virtual Server', or 'NAT' settings",
                "3. Add a new port forwarding rule:",
                f"   - External Port: {APP_PORT}",
                f"   - Internal IP: {local_ip}",
                f"   - Internal Port: {APP_PORT}",
                "   - Protocol: TCP",
                "4. Save and apply the changes",
                "5. Use 'Test External Access' to verify it works",
            ],
            "notes": [
                "Your router's interface may look different",
                "Some ISPs block incoming connections - contact them if it doesn't work",
                "Consider using a Dynamic DNS service if your IP changes frequently",
            ],
        }


# Singleton instance
_network_service: Optional[NetworkService] = None


def get_network_service() -> NetworkService:
    """Get the network service singleton."""
    global _network_service
    if _network_service is None:
        _network_service = NetworkService()
    return _network_service
