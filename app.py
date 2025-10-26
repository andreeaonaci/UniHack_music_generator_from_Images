import gradio as gr
from modules.music_generator import generate_music
from datasets.monuments import load_monuments, match_monument_by_name
import json, os
from PIL import Image

def build_markers_json():
    monuments = load_monuments()
    markers = []
    for m in monuments:
        if m.get("lat") is not None and m.get("lon") is not None:
            markers.append({
                "name": m["nume"],
                "lat": m["lat"],
                "lon": m["lon"],
                "image": m.get("image"),
                "desc": m.get("descriere", "")
            })
    return json.dumps(markers)

markers_json = build_markers_json()
monuments_list = [m["nume"] for m in load_monuments()]

os.makedirs("assets", exist_ok=True)
map_html_path = "assets/map.html"
with open(map_html_path, "w", encoding="utf-8") as f:
    f.write(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html, body {{margin:0; padding:0;}}
  #map {{width: 100%; height: 480px; border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.15);}}
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const markers = {markers_json};
const map = L.map('map', {{zoomControl:true}}).setView([45.94,24.97],7);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom:19}}).addTo(map);

const defaultIcon = L.icon({{
    iconUrl:'https://cdn-icons-png.flaticon.com/512/684/684908.png',
    iconSize:[28,28],
    iconAnchor:[14,28],
    popupAnchor:[0,-28]
}});

markers.forEach(m => {{
    if(!m.lat || !m.lon) return;
    const marker = L.marker([m.lat,m.lon], {{icon:defaultIcon}}).addTo(map);
    const imgHtml = m.image ? `<img src="${{m.image}}" style="width:120px;border-radius:8px;margin-bottom:8px;display:block;">` : "";
    const descShort = m.desc ? (m.desc.length>200?m.desc.substring(0,200)+'...':m.desc) : '';
    const popupHtml = `<div style="text-align:left;max-width:260px;">${{imgHtml}}<strong>${{m.name}}</strong><p style="font-size:12px;color:#333;margin:8px 0;">${{descShort}}</p></div>`;
    marker.bindPopup(popupHtml, {{maxWidth:280}});
}});

function addNearbyMarkers(nearbyMonuments){{
    if(window.tempMarkers) window.tempMarkers.forEach(m => map.removeLayer(m));
    window.tempMarkers = [];
    if(!nearbyMonuments || nearbyMonuments.length === 0) return;
    const first = nearbyMonuments[0];
    const searchCircle = L.circle([first.lat, first.lon], {{
        radius: 50000,
        color: 'red',
        fill: false,
        weight: 2,
        dashArray: '5,5'
    }}).addTo(map);
    window.tempMarkers.push(searchCircle);
    nearbyMonuments.forEach(m => {{
        if(!m.lat || !m.lon) return;
        const icon = L.divIcon({{
            html: `<img src="${{m.image || 'https://cdn-icons-png.flaticon.com/512/684/684908.png'}}" style="width:50px;height:50px;border-radius:50%;border:2px solid white;box-shadow:0 4px 12px rgba(0,0,0,0.3);">`,
            className: ''
        }});
        const marker = L.marker([m.lat, m.lon], {{icon: icon}}).addTo(map);
        const descShort = m.desc ? (m.desc.length > 200 ? m.desc.substring(0,200)+'...' : m.desc) : '';
        const popupHtml = `<div style="text-align:left;max-width:240px;"><strong>${{m.name}}</strong><p style="font-size:12px;color:#333;margin:4px 0;">${{descShort}}</p></div>`;
        marker.bindPopup(popupHtml, {{maxWidth:250}});
        window.tempMarkers.push(marker);
    }});
    map.setView([first.lat, first.lon], 10);
}}

window.addEventListener('message', (e) => {{
    if(e.data?.type === 'addNearby'){{
        addNearbyMarkers(e.data.monuments);
    }}
}});
</script>
</body>
</html>
""")

def process_monument_ui(monument_name):
    monument = match_monument_by_name(monument_name)
    caption = monument.get("descriere","")
    image = "datasets/" + monument.get("image")
    music_path = generate_music(caption, output_path="assets/generated_music.wav")
    # music_path = "assets/generated_music.wav" #generate_music(caption, output_path="assets/generated_music.wav")
    return caption, music_path, image

# === Coordonate România ===
lat_max, lat_min = 48.27, 43.63
lon_min, lon_max = 20.26, 29.65
search_radius = 0.25

with gr.Blocks(css="body {background: linear-gradient(to right,#f0f4ff,#d9e4ff);} .card {border-radius:15px;box-shadow:0 8px 20px rgba(0,0,0,0.18);padding:12px;}") as demo:
    gr.Markdown("<h1 style='text-align:center;color:#4B0082;'>🎵 Monument History AI — Harta Interactivă</h1>")

    gr.Markdown("### 🖱️ Click pe harta statică pentru coordonate")
    click_img = gr.Image(value="assets/harta_romaniei.jpg", interactive=True)
    click_output = gr.Textbox(label="Coordonate click", interactive=False, lines=2)
    monument_dropdown = gr.Dropdown(label="Monumente găsite", choices=[], multiselect=False, interactive=True)
    generate_btn = gr.Button("🎶 Generează muzică")

    with gr.Row():
        with gr.Column():
            image_card = gr.Image(label="Imagine monument", type="filepath")
        with gr.Column():
            music_out = gr.Audio(label="Muzică generată", autoplay=True)
    caption_out = gr.Textbox(label="Descriere generată", interactive=False, lines=3, max_lines=12, autoscroll=True)
    def handle_click(evt: gr.SelectData):
        if evt is None:
            return "No click detected", []
        x_px, y_px = evt.index
        img = Image.open("assets/harta_romaniei.jpg")
        w, h = img.size
        x, y = x_px / w, y_px / h
        lat = lat_max - y * (lat_max - lat_min)
        lon = lon_min + x * (lon_max - lon_min)
        nearby_monuments = []
        for m in load_monuments():
            if m.get("lat") is None or m.get("lon") is None:
                continue
            if abs(m["lat"] - lat) <= search_radius and abs(m["lon"] - lon) <= search_radius:
                nearby_monuments.append(m)
        nearby_names = [m["nume"] for m in nearby_monuments]
        print(f"[DEBUG] Found {len(nearby_monuments)} nearby monuments")
        return f"Click: ({lat:.5f}, {lon:.5f}) — {len(nearby_monuments)} monumente", gr.update(choices=nearby_names, value=None)

    click_img.select(fn=handle_click, inputs=None, outputs=[click_output, monument_dropdown])

    generate_btn.click(
        fn=process_monument_ui,
        inputs=[monument_dropdown],
        outputs=[caption_out, music_out, image_card]
    )

    js_bridge = """
    <script>
    const iframe = document.querySelector('iframe');
    document.addEventListener('gradio:input_changed', (evt) => {
        if(evt.target.id === 'Monumente găsite'){  
            const monuments = evt.target.value;
            if(iframe) iframe.contentWindow.postMessage({type:'addNearby', monuments}, '*');
        }
    });
    </script>
    """
    gr.HTML(js_bridge)

demo.launch(allowed_paths=["."])
