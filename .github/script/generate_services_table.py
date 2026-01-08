# 23.12.25 

import re
from pathlib import Path
from typing import List, Tuple
from datetime import datetime


def extract_service_info(init_file: Path) -> Tuple[str, str, bool, bool, str, str]:
    """
    Extract _stream_type, _drm, _deprecate, _maxResolution, and _region from a services __init__.py file
    
    Args:
        init_file: Path to the __init__.py file
        
    Returns:
        Tuple of (service_name, stream_type, drm, deprecate, max_resolution, region)
    """
    service_name = init_file.parent.name
    stream_type = "N/A"
    drm = False
    deprecate = False
    max_resolution = "N/A"
    region = "N/A"
    
    try:
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Extract _stream_type
            stream_match = re.search(r'_stream_type\s*=\s*["\'](\w+)["\']', content)
            if stream_match:
                stream_type = stream_match.group(1)
            
            # Extract _drm
            drm_match = re.search(r'_drm\s*=\s*(True|False)', content)
            if drm_match:
                drm = drm_match.group(1) == 'True'
            
            # Extract _deprecate
            deprecate_match = re.search(r'_deprecate\s*=\s*(True|False)', content)
            if deprecate_match:
                deprecate = deprecate_match.group(1) == 'True'
            
            # Extract _maxResolution
            resolution_match = re.search(r'_maxResolution\s*=\s*["\']([\w\s]+)["\']', content)
            if resolution_match:
                max_resolution = resolution_match.group(1)
            
            # Extract _region
            region_match = re.search(r'_region\s*=\s*["\']([\w\s]+)["\']', content)
            if region_match:
                region = region_match.group(1)
    
    except Exception as e:
        print(f"Error reading {init_file}: {e}")
    
    return service_name, stream_type, drm, deprecate, max_resolution, region


def find_service_files(base_path: Path) -> List[Path]:
    """
    Find all service __init__.py files
    
    Args:
        base_path: Base path of the project
        
    Returns:
        List of paths to service __init__.py files
    """
    services_path = base_path / "StreamingCommunity" / "services"
    init_files = []
    
    if not services_path.exists():
        print(f"Services path not found: {services_path.resolve()}")
        return init_files
    
    # Iterate through service directories
    for service_dir in services_path.iterdir():
        if service_dir.is_dir() and not service_dir.name.startswith('__'):
            init_file = service_dir / "__init__.py"
            if init_file.exists():
                init_files.append(init_file)
    
    return sorted(init_files)


def generate_markdown_table(services: List[Tuple[str, str, bool, str, str]]) -> str:
    """
    Generate markdown table from services data with dynamic column widths
    Only includes services where _deprecate = False
    
    Args:
        services: List of (service_name, stream_type, drm, max_resolution, region) tuples
        
    Returns:
        Markdown formatted table
    """
    services = sorted(services, key=lambda x: x[0].lower())
    
    # Prepare data with display names
    table_data = []
    for service_name, stream_type, drm, max_resolution, region in services:
        display_name = service_name.replace('_', ' ').title()
        drm_icon = "✅" if drm else "❌"
        table_data.append((display_name, stream_type, drm_icon, max_resolution, region))
    
    # Calculate maximum width for each column
    col1_header = "Site Name"
    col2_header = "Stream Type"
    col3_header = "DRM"
    col4_header = "Max Resolution"
    col5_header = "Region"
    
    # Start with header widths
    max_col1 = len(col1_header)
    max_col2 = len(col2_header)
    max_col3 = len(col3_header)
    max_col4 = len(col4_header)
    max_col5 = len(col5_header)
    
    # Check all data rows
    for display_name, stream_type, drm_icon, max_resolution, region in table_data:
        max_col1 = max(max_col1, len(display_name))
        max_col2 = max(max_col2, len(stream_type))
        max_col3 = max(max_col3, len(drm_icon))
        max_col4 = max(max_col4, len(max_resolution))
        max_col5 = max(max_col5, len(region))
    
    # Build table with dynamic widths
    lines = ["# Services Overview", ""]
    
    # Header row
    header = f"| {col1_header.ljust(max_col1)} | {col2_header.ljust(max_col2)} | {col3_header.ljust(max_col3)} | {col4_header.ljust(max_col4)} | {col5_header.ljust(max_col5)} |"
    lines.append(header)
    
    # Separator row
    separator = f"|{'-' * (max_col1 + 2)}|{'-' * (max_col2 + 2)}|{'-' * (max_col3 + 2)}|{'-' * (max_col4 + 2)}|{'-' * (max_col5 + 2)}|"
    lines.append(separator)
    
    # Data rows
    for display_name, stream_type, drm_icon, max_resolution, region in table_data:
        row = f"| {display_name.ljust(max_col1)} | {stream_type.ljust(max_col2)} | {drm_icon.ljust(max_col3)} | {max_resolution.ljust(max_col4)} | {region.ljust(max_col5)} |"
        lines.append(row)
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    return "\n".join(lines)


def main():
    script_dir = Path(__file__).parent
    base_path = script_dir.parent.parent
    print(f"Base path: {base_path}")

    # Find all service __init__.py files
    init_files = find_service_files(base_path)
    print(f"Found {len(init_files)} service files")
    
    if not init_files:
        print("No service files found!")
        return
    
    # Extract information from each service
    services = []
    deprecated_count = 0
    for init_file in init_files:
        service_name, stream_type, drm, deprecate, max_resolution, region = extract_service_info(init_file)
        
        # Only include services that are not deprecated
        if not deprecate and stream_type != "N/A":
            services.append((service_name, stream_type, drm, max_resolution, region))
        else:
            deprecated_count += 1
    
    print(f"Deprecated services: {deprecated_count}")
    
    # Generate markdown table
    markdown_content = generate_markdown_table(services)
    
    # Write to site.md
    output_file = base_path / ".github" / "doc" / "site.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)


if __name__ == "__main__":
    main()