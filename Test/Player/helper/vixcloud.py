
import os
import sys
import json


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Api.Player.Helper.Vixcloud.js_parser import JavaScriptParser
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import WindowVideo, WindowParameter, StreamsCollection


# Data
script_text = '''
  window.video = {"id":271977,"name":"Smile 2","filename":"Smile.2.2024.1080p.WEB-DL.DDP5.1.H.264-FHC.mkv","size":10779891,"quality":1080,"duration":7758,"views":0,"is_viewable":1,"status":"public","fps":24,"legacy":0,"folder_id":"301e469a-786f-493a-ad2b-302248aa2d23","created_at_diff":"4 giorni fa"};
        window.streams = [{"name":"Server1","active":false,"url":"https:\/\/vixcloud.co\/playlist\/271977?b=1\u0026ub=1"},{"name":"Server2","active":1,"url":"https:\/\/vixcloud.co\/playlist\/271977?b=1\u0026ab=1"}];
        window.masterPlaylist = {
            params: {
                'token': '890a3e7db7f1c8213a11007947362b21',
                'expires': '1737812156',
            },
            url: 'https://vixcloud.co/playlist/271977?b=1',
        }
        window.canPlayFHD = true
'''


# Test
converter = JavaScriptParser.parse(js_string=str(script_text))
json_string = json.dumps(converter, indent=2)
print("Converted json: ", json_string, "\n")

window_video = WindowVideo(converter.get('video'))
window_streams = StreamsCollection(converter.get('streams'))
window_parameter = WindowParameter(converter.get('masterPlaylist'))

print(window_video)
print(window_streams)
print(window_parameter)