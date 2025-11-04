"""
Canva to PDF Converter

This module provides functionality to interact with Canva's API and export designs to PDF format.
It supports both Canva Connect API and direct export operations.

Author: ACAFI Clipping Agent
Date: 2025-11-04
"""

import requests
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger
from dataclasses import dataclass
from enum import Enum


class ExportFormat(Enum):
    """Supported export formats from Canva"""
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    PDF_STANDARD = "pdf_standard"
    PDF_PRINT = "pdf_print"


class ExportQuality(Enum):
    """Export quality settings"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CanvaExportResult:
    """Result of a Canva export operation"""
    success: bool
    file_path: Optional[Path] = None
    url: Optional[str] = None
    error: Optional[str] = None
    export_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CanvaAPIError(Exception):
    """Custom exception for Canva API errors"""
    pass


class CanvaToPDFConverter:
    """
    Main class for converting Canva designs to PDF.

    This class handles authentication, export requests, and file downloads
    from the Canva API.
    """

    # Canva API endpoints
    API_BASE_URL = "https://api.canva.com/rest/v1"
    CONNECT_BASE_URL = "https://api.canva.com/v1"

    def __init__(
        self,
        api_key: str,
        output_dir: Optional[Path] = None,
        timeout: int = 300,
        max_retries: int = 3
    ):
        """
        Initialize the Canva to PDF converter.

        Args:
            api_key: Canva API key or access token
            output_dir: Directory to save exported PDFs (defaults to ./exports)
            timeout: Maximum time to wait for export completion (seconds)
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.api_key = api_key
        self.output_dir = output_dir or Path("./exports")
        self.timeout = timeout
        self.max_retries = max_retries

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"CanvaToPDFConverter initialized. Output directory: {self.output_dir}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to Canva API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            CanvaAPIError: If the request fails after all retries
        """
        url = f"{self.API_BASE_URL}/{endpoint.lstrip('/')}"

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{self.max_retries})")

                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params,
                    timeout=30
                )

                if response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if attempt == self.max_retries - 1:
                    error_msg = f"HTTP error after {self.max_retries} attempts: {e}"
                    if hasattr(e.response, 'text'):
                        error_msg += f" - Response: {e.response.text}"
                    logger.error(error_msg)
                    raise CanvaAPIError(error_msg)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    error_msg = f"Request error after {self.max_retries} attempts: {e}"
                    logger.error(error_msg)
                    raise CanvaAPIError(error_msg)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)

        raise CanvaAPIError("Max retries exceeded")

    def export_design_to_pdf(
        self,
        design_id: str,
        filename: Optional[str] = None,
        quality: ExportQuality = ExportQuality.HIGH,
        pages: Optional[List[int]] = None
    ) -> CanvaExportResult:
        """
        Export a Canva design to PDF format.

        Args:
            design_id: Canva design ID (from URL or API)
            filename: Optional custom filename (without extension)
            quality: Export quality setting
            pages: Optional list of page numbers to export (1-indexed)

        Returns:
            CanvaExportResult with export status and file path
        """
        try:
            logger.info(f"Starting PDF export for design: {design_id}")

            # Prepare export request
            export_data = {
                "design_id": design_id,
                "format": ExportFormat.PDF.value,
                "quality": quality.value
            }

            if pages:
                export_data["pages"] = pages

            # Request export
            logger.debug(f"Requesting export with data: {export_data}")
            export_response = self._make_request("POST", "/exports", data=export_data)

            export_id = export_response.get("export", {}).get("id")
            if not export_id:
                raise CanvaAPIError("No export ID received from API")

            logger.info(f"Export job created with ID: {export_id}")

            # Poll for export completion
            download_url = self._wait_for_export(export_id)

            # Download the PDF
            file_path = self._download_file(download_url, design_id, filename)

            logger.info(f"Successfully exported PDF to: {file_path}")

            return CanvaExportResult(
                success=True,
                file_path=file_path,
                url=download_url,
                export_id=export_id,
                metadata={
                    "design_id": design_id,
                    "quality": quality.value,
                    "pages": pages
                }
            )

        except Exception as e:
            error_msg = f"Failed to export design {design_id} to PDF: {str(e)}"
            logger.error(error_msg)
            return CanvaExportResult(
                success=False,
                error=error_msg
            )

    def _wait_for_export(self, export_id: str) -> str:
        """
        Poll the export status until completion.

        Args:
            export_id: Export job ID

        Returns:
            Download URL for the exported file

        Raises:
            CanvaAPIError: If export fails or times out
        """
        start_time = time.time()
        poll_interval = 2  # seconds

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise CanvaAPIError(f"Export timeout after {self.timeout} seconds")

            # Check export status
            status_response = self._make_request("GET", f"/exports/{export_id}")
            status = status_response.get("export", {}).get("status")

            logger.debug(f"Export status: {status} (elapsed: {elapsed:.1f}s)")

            if status == "success":
                download_url = status_response.get("export", {}).get("url")
                if not download_url:
                    raise CanvaAPIError("Export succeeded but no download URL provided")
                return download_url

            elif status == "failed":
                error = status_response.get("export", {}).get("error", "Unknown error")
                raise CanvaAPIError(f"Export failed: {error}")

            elif status in ["in_progress", "pending"]:
                time.sleep(poll_interval)

            else:
                raise CanvaAPIError(f"Unknown export status: {status}")

    def _download_file(
        self,
        url: str,
        design_id: str,
        custom_filename: Optional[str] = None
    ) -> Path:
        """
        Download the exported file from Canva.

        Args:
            url: Download URL
            design_id: Design ID for naming
            custom_filename: Optional custom filename

        Returns:
            Path to downloaded file

        Raises:
            CanvaAPIError: If download fails
        """
        try:
            # Generate filename
            if custom_filename:
                filename = f"{custom_filename}.pdf"
            else:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"canva_export_{design_id}_{timestamp}.pdf"

            file_path = self.output_dir / filename

            logger.info(f"Downloading file to: {file_path}")

            # Download file
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            # Save to disk
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = file_path.stat().st_size
            logger.info(f"Download complete. File size: {file_size / 1024:.2f} KB")

            return file_path

        except Exception as e:
            raise CanvaAPIError(f"Failed to download file: {str(e)}")

    def get_design_info(self, design_id: str) -> Dict[str, Any]:
        """
        Get information about a Canva design.

        Args:
            design_id: Canva design ID

        Returns:
            Design metadata
        """
        try:
            logger.info(f"Fetching design info for: {design_id}")
            response = self._make_request("GET", f"/designs/{design_id}")
            return response.get("design", {})
        except Exception as e:
            logger.error(f"Failed to get design info: {e}")
            return {}

    def list_exports(self, design_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List export jobs, optionally filtered by design ID.

        Args:
            design_id: Optional design ID to filter exports

        Returns:
            List of export job details
        """
        try:
            params = {"design_id": design_id} if design_id else None
            response = self._make_request("GET", "/exports", params=params)
            return response.get("exports", [])
        except Exception as e:
            logger.error(f"Failed to list exports: {e}")
            return []

    def export_from_url(self, canva_url: str, filename: Optional[str] = None) -> CanvaExportResult:
        """
        Export a Canva design to PDF using its share URL.

        Args:
            canva_url: Full Canva design URL (e.g., https://www.canva.com/design/XXXXX/...)
            filename: Optional custom filename

        Returns:
            CanvaExportResult with export status
        """
        try:
            # Extract design ID from URL
            design_id = self._extract_design_id(canva_url)
            logger.info(f"Extracted design ID: {design_id} from URL: {canva_url}")

            # Export the design
            return self.export_design_to_pdf(design_id, filename)

        except Exception as e:
            error_msg = f"Failed to export from URL {canva_url}: {str(e)}"
            logger.error(error_msg)
            return CanvaExportResult(success=False, error=error_msg)

    def _extract_design_id(self, canva_url: str) -> str:
        """
        Extract design ID from a Canva URL.

        Args:
            canva_url: Canva design URL

        Returns:
            Design ID

        Raises:
            ValueError: If URL format is invalid
        """
        # Example URL: https://www.canva.com/design/DAFxxxxx/view
        # or: https://www.canva.com/design/DAFxxxxx/edit

        if "canva.com/design/" not in canva_url:
            raise ValueError(f"Invalid Canva URL format: {canva_url}")

        parts = canva_url.split("/design/")
        if len(parts) < 2:
            raise ValueError(f"Could not extract design ID from URL: {canva_url}")

        design_id = parts[1].split("/")[0]

        if not design_id:
            raise ValueError(f"Empty design ID extracted from URL: {canva_url}")

        return design_id


def convert_canva_to_pdf(
    design_id_or_url: str,
    api_key: str,
    output_dir: Optional[str] = None,
    filename: Optional[str] = None,
    quality: str = "high"
) -> CanvaExportResult:
    """
    Convenience function to convert a Canva design to PDF.

    Args:
        design_id_or_url: Canva design ID or full URL
        api_key: Canva API key
        output_dir: Optional output directory
        filename: Optional custom filename
        quality: Export quality ('low', 'medium', 'high')

    Returns:
        CanvaExportResult with export status

    Example:
        >>> result = convert_canva_to_pdf(
        ...     "https://www.canva.com/design/DAFxxxxx/view",
        ...     api_key="your-api-key",
        ...     filename="my_design"
        ... )
        >>> if result.success:
        ...     print(f"PDF saved to: {result.file_path}")
    """
    converter = CanvaToPDFConverter(
        api_key=api_key,
        output_dir=Path(output_dir) if output_dir else None
    )

    quality_enum = ExportQuality[quality.upper()]

    # Check if input is URL or ID
    if "canva.com" in design_id_or_url:
        return converter.export_from_url(design_id_or_url, filename)
    else:
        return converter.export_design_to_pdf(design_id_or_url, filename, quality_enum)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 3:
        print("Usage: python canva_to_pdf.py <design_id_or_url> <api_key> [output_dir] [filename]")
        sys.exit(1)

    design = sys.argv[1]
    api_key = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    filename = sys.argv[4] if len(sys.argv) > 4 else None

    result = convert_canva_to_pdf(design, api_key, output_dir, filename)

    if result.success:
        print(f"✓ Success! PDF saved to: {result.file_path}")
    else:
        print(f"✗ Error: {result.error}")
        sys.exit(1)
