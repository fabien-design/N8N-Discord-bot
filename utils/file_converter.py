"""
File type converter for N8N Data Loader compatibility.
Converts unsupported file types to supported formats.
"""

import io
from typing import Tuple, Optional


# N8N Data Loader supported MIME types for document processing
SUPPORTED_MIME_TYPES = {
    # Text formats
    'text/plain',
    'text/csv',
    'text/html',

    # Documents
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # XLSX
    'application/vnd.oasis.opendocument.text',  # ODT

    # JSON/structured data
    'application/json',
}

# Mapping of unsupported types to supported conversions
MIME_TYPE_CONVERSIONS = {
    # Markdown -> Plain Text
    'text/markdown': 'text/plain',
    'text/x-markdown': 'text/plain',

    # Legacy Office formats -> DOCX equivalent (treat as text)
    'application/msword': 'text/plain',  # DOC
    'application/vnd.ms-excel': 'text/plain',  # XLS

    # Code files -> Plain Text
    'text/x-python': 'text/plain',
    'text/x-java': 'text/plain',
    'text/x-c': 'text/plain',
    'text/x-c++': 'text/plain',
    'application/javascript': 'text/plain',
    'application/typescript': 'text/plain',
    'text/x-sh': 'text/plain',

    # Config files -> Plain Text
    'application/x-yaml': 'text/plain',
    'text/yaml': 'text/plain',
    'application/toml': 'text/plain',
    'text/x-toml': 'text/plain',
    'application/xml': 'text/plain',
    'text/xml': 'text/plain',

    # Other text-based formats
    'text/x-rst': 'text/plain',  # ReStructuredText
    'text/x-tex': 'text/plain',  # LaTeX
}

# File extensions to MIME type mapping (fallback)
EXTENSION_TO_MIME = {
    '.md': 'text/markdown',
    '.markdown': 'text/markdown',
    '.txt': 'text/plain',
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc': 'application/msword',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
    '.csv': 'text/csv',
    '.json': 'application/json',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.py': 'text/x-python',
    '.js': 'application/javascript',
    '.ts': 'application/typescript',
    '.java': 'text/x-java',
    '.c': 'text/x-c',
    '.cpp': 'text/x-c++',
    '.yaml': 'application/x-yaml',
    '.yml': 'application/x-yaml',
    '.toml': 'application/toml',
    '.xml': 'application/xml',
    '.sh': 'text/x-sh',
}


def get_mime_type_from_filename(filename: str) -> Optional[str]:
    """
    Get MIME type from filename extension.

    Args:
        filename: The filename to check

    Returns:
        MIME type string or None
    """
    for ext, mime in EXTENSION_TO_MIME.items():
        if filename.lower().endswith(ext):
            return mime
    return None


def is_supported_mime_type(mime_type: str) -> bool:
    """
    Check if MIME type is supported by N8N Data Loader.

    Args:
        mime_type: MIME type to check

    Returns:
        True if supported, False otherwise
    """
    return mime_type in SUPPORTED_MIME_TYPES


def get_converted_mime_type(original_mime: str, filename: str) -> Tuple[str, str]:
    """
    Get the converted MIME type and new filename for unsupported types.

    Args:
        original_mime: Original MIME type
        filename: Original filename

    Returns:
        Tuple of (converted_mime_type, new_filename)
    """
    # If already supported, return as-is
    if is_supported_mime_type(original_mime):
        return original_mime, filename

    # Check if we have a direct conversion mapping
    if original_mime in MIME_TYPE_CONVERSIONS:
        converted_mime = MIME_TYPE_CONVERSIONS[original_mime]

        # Update filename extension based on converted type
        new_filename = _update_filename_extension(filename, converted_mime)

        return converted_mime, new_filename

    # Try to determine from filename
    mime_from_filename = get_mime_type_from_filename(filename)
    if mime_from_filename and mime_from_filename in MIME_TYPE_CONVERSIONS:
        converted_mime = MIME_TYPE_CONVERSIONS[mime_from_filename]
        new_filename = _update_filename_extension(filename, converted_mime)
        return converted_mime, new_filename

    # Default fallback to plain text for unknown text-based formats
    if original_mime and (original_mime.startswith('text/') or
                          'text' in original_mime.lower() or
                          original_mime == 'application/octet-stream'):
        new_filename = _update_filename_extension(filename, 'text/plain')
        return 'text/plain', new_filename

    # If can't convert, return original (may cause issues but let N8N handle it)
    return original_mime, filename


def _update_filename_extension(filename: str, target_mime: str) -> str:
    """
    Update filename extension based on target MIME type.

    Args:
        filename: Original filename
        target_mime: Target MIME type

    Returns:
        Updated filename
    """
    # Remove existing extension
    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename

    # Map MIME type to extension
    mime_to_ext = {
        'text/plain': '.txt',
        'text/csv': '.csv',
        'application/pdf': '.pdf',
        'application/json': '.json',
        'text/html': '.html',
    }

    new_ext = mime_to_ext.get(target_mime, '.txt')
    return f"{base_name}{new_ext}"


def should_convert_file(mime_type: str, filename: str) -> bool:
    """
    Determine if a file needs conversion.

    Args:
        mime_type: File's MIME type
        filename: File's name

    Returns:
        True if conversion is needed
    """
    if not mime_type:
        mime_type = get_mime_type_from_filename(filename) or 'application/octet-stream'

    return not is_supported_mime_type(mime_type)


def get_file_info_for_n8n(original_mime: str, filename: str, file_data: bytes) -> dict:
    """
    Prepare file information for N8N Data Loader with automatic conversion.

    Args:
        original_mime: Original MIME type
        filename: Original filename
        file_data: File content as bytes

    Returns:
        Dictionary with converted file info ready for N8N
    """
    # Get converted MIME type and filename
    converted_mime, new_filename = get_converted_mime_type(original_mime, filename)

    return {
        'filename': new_filename,
        'content_type': converted_mime,
        'original_filename': filename,
        'original_content_type': original_mime,
        'converted': converted_mime != original_mime
    }
