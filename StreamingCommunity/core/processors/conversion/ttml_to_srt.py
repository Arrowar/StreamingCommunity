# 10.01.24

import re
import html
import xml.etree.ElementTree as ET
from pathlib import Path


# External import 
from rich.console import Console


# Variable
console = Console()


def parse_time_expression(time_str):
    """
    Parse TTML time expression and convert to seconds.
    Supports formats like: HH:MM:SS.mmm, HH:MM:SS:frames, seconds
    """
    time_str = time_str.strip()
    
    # Format: HH:MM:SS.mmm or HH:MM:SS,mmm
    if ':' in time_str:

        # Replace comma with dot for milliseconds
        time_str = time_str.replace(',', '.')
        
        # Handle frames notation (HH:MM:SS:FF)
        if time_str.count(':') == 3:
            hours, minutes, seconds, frames = time_str.split(':')
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds) + int(frames) / 25.0
        else:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            total_seconds = hours * 3600 + minutes * 60 + seconds
    else:
        # Assume it's already in seconds
        time_str = time_str.rstrip('s')
        try:
            total_seconds = float(time_str)
        except ValueError:
            return 0.0
    
    return total_seconds


def seconds_to_srt_time(seconds):
    """
    Convert seconds to SRT time format: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def clean_text(element):
    """
    Extract and clean text from XML element, preserving line breaks
    Properly handles HTML entities and spacing
    """
    def get_all_text(elem, parts):
        """Recursively extract text from element and children"""
        # Add text before children
        if elem.text:
            text = elem.text.strip()
            if text:

                # Decode HTML entities
                text = html.unescape(text)
                parts.append(text)
        
        # Process children
        for child in elem:

            # Handle <br/> elements
            if child.tag.endswith('br'):
                parts.append('\n')
            else:
                # Recursively process child
                get_all_text(child, parts)
            
            # Add tail text (text after child element)
            if child.tail:
                tail = child.tail.strip()
                if tail:

                    # Decode HTML entities
                    tail = html.unescape(tail)
                    parts.append(tail)
    
    text_parts = []
    get_all_text(element, text_parts)
    
    # Join parts with proper spacing
    result = []
    for i, part in enumerate(text_parts):
        if part == '\n':
            result.append('\n')
        else:
            # Add space between parts unless it's after a newline
            if result and result[-1] != '\n' and i > 0:
                result.append(' ')
            result.append(part)
    
    text = ''.join(result)
    
    # Clean up multiple spaces and newlines
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n ', '\n', text)
    text = re.sub(r' \n', '\n', text)
    text = re.sub(r'\n+', '\n', text)
    
    return text.strip()


def extract_xml_from_binary(file_path):
    """
    Extract XML content from binary TTML files (e.g., DASH/MP4 containers)
    """
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Try to decode as text first
    try:
        text_content = content.decode('utf-8')
        if '<?xml' in text_content:
            return text_content
    except Exception:
        pass
    
    # Look for XML patterns in binary data
    xml_parts = []
    content_str = content.decode('utf-8', errors='ignore')
    
    # Find all XML declarations
    xml_start = 0
    while True:
        xml_start = content_str.find('<?xml', xml_start)
        if xml_start == -1:
            break
        
        # Find the end of this XML document
        xml_end = content_str.find('</tt>', xml_start)
        if xml_end != -1:
            xml_end += 5  # Include </tt>
            xml_chunk = content_str[xml_start:xml_end]
            
            # Only add chunks that have actual content (paragraphs)
            if '<p ' in xml_chunk or '<p>' in xml_chunk:
                xml_parts.append(xml_chunk)
        
        xml_start += 1
    
    return xml_parts if xml_parts else None


def convert_ttml_to_srt(ttml_path, srt_path=None):
    """
    Convert TTML file to SRT format
    """
    # Try to extract XML from potentially binary file
    xml_content = extract_xml_from_binary(ttml_path)
    
    if not xml_content:
        console.print(f"[red]Cant't extract XML content from {ttml_path}. Is it a valid TTML file?")
        return False
    
    # If multiple XML chunks found, merge them
    all_subtitles = []
    
    if isinstance(xml_content, list):
        xml_chunks = xml_content
    else:
        xml_chunks = [xml_content]
    
    for idx, xml_chunk in enumerate(xml_chunks):
        try:
            root = ET.fromstring(xml_chunk)
        except ET.ParseError as e:
            console.print(f"[yellow]Warning: Failed to parse XML chunk {idx+1}: {e}. Skipping this chunk.")
            continue
    
        # Find namespace
        namespace = {'': ''}
        if root.tag.startswith('{'):
            namespace_match = re.match(r'\{(.*?)\}', root.tag)
            if namespace_match:
                ns_uri = namespace_match.group(1)
                namespace = {'tt': ns_uri}
        
        # Find all subtitle entries
        paragraphs = root.findall('.//tt:p', namespace)
        if not paragraphs:
            paragraphs = root.findall('.//{*}p')
        if not paragraphs:
            paragraphs = root.findall('.//p')
        
        # Extract subtitles from this chunk
        for p in paragraphs:
            begin = p.get('begin')
            end = p.get('end')
            
            if not begin or not end:
                continue
            
            try:
                start_seconds = parse_time_expression(begin)
                end_seconds = parse_time_expression(end)
                text = clean_text(p)
                
                if text:  # Only add if there's actual text
                    all_subtitles.append({
                        'start': start_seconds,
                        'end': end_seconds,
                        'text': text
                    })
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to process subtitle: {e}")
                continue
    
    subtitles = all_subtitles
    
    if not subtitles:
        console.print("[red]No valid subtitles extracted")
        return False
    
    # Sort by start time
    subtitles.sort(key=lambda x: x['start'])
    
    # Generate output path if not provided
    if srt_path is None:
        srt_path = Path(ttml_path).with_suffix('.srt')
    
    # Write SRT file
    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                f.write(f"{i}\n")
                f.write(f"{seconds_to_srt_time(sub['start'])} --> {seconds_to_srt_time(sub['end'])}\n")
                f.write(f"{sub['text']}\n")
                f.write("\n")
        
        return True
    except Exception as e:
        console.print(f"[red]Error writing file: {e}")
        return False