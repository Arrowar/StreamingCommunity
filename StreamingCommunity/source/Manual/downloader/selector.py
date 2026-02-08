# 19.05.25


class StreamSelector:
    @staticmethod
    def parse_filter(filter_str):
        """Parse filter string like 'res=1920:for=best' or 'lang='ita|eng':for=all'"""
        parts = {}
        
        if filter_str.lower() == 'best':
            return {'for': 'best'}
        
        if filter_str.lower() == 'all':
            return {'for': 'all'}
        
        for part in filter_str.split(':'):
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                parts[key] = value
        
        return parts
    
    @staticmethod
    def select_video(streams, filter_str):
        """Select video streams based on filter"""
        video_streams = [s for s in streams if s.type == 'video']
        if not video_streams:
            return []
        
        parsed = StreamSelector.parse_filter(filter_str)
        
        # If 'for=best' without res, select highest bitrate
        if parsed.get('for') == 'best' and 'res' not in parsed:
            best_stream = max(video_streams, key=lambda s: s.bitrate)
            best_stream.selected = True
            return [best_stream]
        
        # If res specified
        if 'res' in parsed:
            target_res = int(parsed['res'])
            matching = [s for s in video_streams if s.width == target_res or s.height == target_res]
            
            if matching:
                if parsed.get('for') == 'best':
                    best_stream = max(matching, key=lambda s: s.bitrate)
                    best_stream.selected = True
                    return [best_stream]
                else:
                    for s in matching:
                        s.selected = True
                    return matching
        
        # Default: select best
        best_stream = max(video_streams, key=lambda s: s.bitrate)
        best_stream.selected = True
        return [best_stream]
    
    @staticmethod
    def select_audio(streams, filter_str):
        """Select audio streams based on filter"""
        audio_streams = [s for s in streams if s.type == 'audio']
        if not audio_streams:
            return []
        
        parsed = StreamSelector.parse_filter(filter_str)
        
        # If 'all', select all
        if filter_str.lower() == 'all':
            for s in audio_streams:
                s.selected = True
            return audio_streams
        
        # If lang specified
        if 'lang' in parsed:
            lang_patterns = parsed['lang'].split('|')
            matching = []
            
            for stream in audio_streams:
                for pattern in lang_patterns:
                    if pattern.lower() == stream.language.lower() or pattern.lower() in stream.language.lower():
                        matching.append(stream)
                        break
            
            if matching:
                if parsed.get('for') == 'best':
                    best_stream = max(matching, key=lambda s: s.bitrate)
                    best_stream.selected = True
                    return [best_stream]
                else:
                    for s in matching:
                        s.selected = True
                    return matching
        
        # Default: select best
        best_stream = max(audio_streams, key=lambda s: s.bitrate)
        best_stream.selected = True
        return [best_stream]
    
    @staticmethod
    def select_subtitle(streams, filter_str):
        """Select subtitle streams based on filter"""
        subtitle_streams = [s for s in streams if s.type == 'subtitle']
        if not subtitle_streams:
            return []
        
        parsed = StreamSelector.parse_filter(filter_str)
        
        # If 'all', select all
        if filter_str.lower() == 'all':
            for s in subtitle_streams:
                s.selected = True
            return subtitle_streams
        
        # If lang specified
        if 'lang' in parsed:
            lang_patterns = parsed['lang'].split('|')
            matching = []
            
            for stream in subtitle_streams:
                for pattern in lang_patterns:
                    if pattern.lower() == stream.language.lower() or pattern.lower() in stream.language.lower():
                        matching.append(stream)
                        break
            
            if matching:
                if parsed.get('for') == 'all':
                    for s in matching:
                        s.selected = True
                    return matching
                elif parsed.get('for') == 'best':
                    matching[0].selected = True
                    return [matching[0]]
                else:
                    for s in matching:
                        s.selected = True
                    return matching
        
        return []