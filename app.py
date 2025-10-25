import gradio as gr
from modules.music_generator import generate_music
from datasets.monuments import load_monuments, match_monument_by_name
import json, os
from PIL import Image
import numpy as np

# === Construire markere pentru harta Leaflet ===
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

# === Scriere map.html pentru Leaflet ===
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
const icon = L.icon({{iconUrl:'https://cdn-icons-png.flaticon.com/512/684/684908.png',iconSize:[28,28],iconAnchor:[14,28],popupAnchor:[0,-28]}});

markers.forEach(m => {{
    const marker = L.marker([m.lat,m.lon], {{icon}}).addTo(map);
    const imgHtml = m.image ? `<img src="${{m.image}}" style="width:120px;border-radius:8px;margin-bottom:8px;display:block;">` : "";
    const descShort = m.desc ? (m.desc.length>200?m.desc.substring(0,200)+'...':m.desc) : '';
    const popupHtml = `
        <div style="text-align:left;max-width:260px;">
            ${{imgHtml}}
            <strong>${{m.name}}</strong>
            <p style="font-size:12px;color:#333;margin:8px 0;">${{descShort}}</p>
            <button onclick="selectMonument('${{m.name.replace(/'/g,'\\\\')}}')" style="background:#4B0082;color:white;border:none;padding:8px 10px;border-radius:8px;cursor:pointer;">Select</button>
        </div>`;
    marker.bindPopup(popupHtml, {{maxWidth:280}});
}});

function selectMonument(name){{
    window.parent.postMessage({{type:'selectMonument',name}}, '*');
}}
</script>
</body>
</html>
""")

# === JS bridge între iframe și Gradio ===
js_bridge = """
<script>
window.addEventListener('message', (e) => {
    if(e.data?.type === 'selectMonument'){
        const name = e.data.name;
        const selects = document.querySelectorAll('select');
        for(let s of selects){
            for(let opt of s.options){
                if(opt.text === name){
                    s.value = opt.value;
                    s.dispatchEvent(new Event('change'));
                    const btn = document.querySelector('button[title="Generează muzică"]') || document.querySelector('button');
                    if(btn) btn.click();
                    return;
                }
            }
        }
    }
});
</script>
"""

# === Procesare monument ===
def process_monument_ui(monument_name):
    monument = match_monument_by_name(monument_name)
    caption = monument.get("descriere","")
    image = monument.get("image")
    music_path = generate_music(caption, output_path="assets/generated_music.wav")
    return caption, music_path, image

# === Coordonate click pe imagine statică ===
def on_image_click(x, y):
    img = Image.open("assets/harta_romaniei.jpg")
    px = x * img.width
    py = y * img.height
    return f"Pixels: ({px:.1f}, {py:.1f}) | Normalized: ({x:.3f}, {y:.3f})"

# === Interfață Gradio ===
with gr.Blocks(css="body {background: linear-gradient(to right,#f0f4ff,#d9e4ff);} .card {border-radius:15px;box-shadow:0 8px 20px rgba(0,0,0,0.18);padding:12px;}") as demo:

    gr.Markdown("<h1 style='text-align:center;color:#4B0082;'>🎵 Monument History AI — Harta</h1>")

    with gr.Row():
        with gr.Column(scale=1):
            monument_dropdown = gr.Dropdown(choices=monuments_list, label="Selectează monument")
            generate_btn = gr.Button("🎶 Generează muzică")
            gr.Markdown("Apasă un marker pe hartă sau click pe harta statică pentru coordonate.")

        with gr.Column(scale=2):
            gr.HTML(f"<iframe src='{map_html_path}' width='100%' height='480' style='border:none;border-radius:12px;'></iframe>")
            image_card = gr.Image(label="Imagine monument", type="filepath")
            caption_out = gr.Textbox(label="Caption generat", interactive=False)
            music_out = gr.Audio(label="Muzică generată", autoplay=True)

    # Harta statică pentru click exact
    gr.Markdown("### 🖱️ Click pe harta statică")
    click_img = gr.Image(value="assets/harta_romaniei.jpg", interactive=True)
    click_output = gr.Textbox(label="Coordonate click", interactive=False)
    # BOUNDING BOX România
    lat_max = 48.27
    lat_min = 43.63
    lon_min = 20.26
    lon_max = 29.65

    # Event click pe hartă statică
    def handle_click(evt: gr.SelectData):
        if evt is None:
            return "No click detected"

        x_px, y_px = evt.index  # coordonate pixel

        img = Image.open("assets/harta_romaniei.jpg")
        w, h = img.size

        # transformare în coordonate normalizate
        x = x_px / w
        y = y_px / h

        lat_offset = -0.05   # ca să scazi 0.2 grade din latitudine
        lon_offset = -1.1   # ca să scazi 0.6 grade din longitudine

        lat = lat_max - y * (lat_max - lat_min) + lat_offset
        lon = lon_min + x * (lon_max - lon_min) + lon_offset

        return f"""
    Pixel: ({x_px}, {y_px})
    Norm: ({x:.4f}, {y:.4f})
    Lat/Lon: {lat:.5f}, {lon:.5f}
    """

    click_img.select(
        fn=handle_click,
        inputs=None,
        outputs=[click_output]
    )


    generate_btn.click(
        fn=process_monument_ui,
        inputs=[monument_dropdown],
        outputs=[caption_out, music_out, image_card]
    )
    click_img = gr.Image(value="assets/harta_romaniei.jpg", interactive=True)
    click_output = gr.Textbox(label="Coordonate click", interactive=False)
    click_img.select(
        fn=handle_click,
        inputs=None,
        outputs=[click_output]
    )


    gr.HTML(js_bridge)

demo.launch(allowed_paths=["."])
