import gradio as gr
from modules.music_generator import generate_music
from datasets.monuments import load_monuments, match_monument_by_name
import json, os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import math
from modules import settings as app_settings


def build_markers_json():
    monuments = load_monuments()
    markers = []
    for m in monuments:
        if m.get("lat") is not None and m.get("lon") is not None:
            markers.append({
                "name": m["nume"],
                "localitate": m.get("localitate"),
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
    template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html, body {margin:0; padding:0; height:100%;}
  #map {width: 100%; height: 480px; border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.15);}


</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const markers = {MARKERS};
const map = L.map('map', {zoomControl:true}).setView([45.94,24.97],7);

// Fundal harta OSM
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19}).addTo(map);

const defaultIcon = L.icon({
    iconUrl:'https://cdn-icons-png.flaticon.com/512/684/684908.png',
    iconSize:[28,28],
    iconAnchor:[14,28],
    popupAnchor:[0,-28]
});

// dynamic markers management
window.appMarkers = [];
function clearAppMarkers(){
    if(window.appMarkers) window.appMarkers.forEach(m => map.removeLayer(m));
    window.appMarkers = [];
}

function createMarkersFromList(list){
    clearAppMarkers();
    list.forEach(m => {
        if(!m.lat || !m.lon) return;
        const marker = L.marker([m.lat,m.lon], {icon:defaultIcon}).addTo(map);
        const imgHtml = m.image ? `<img src="${m.image}" style="width:120px;border-radius:8px;margin-bottom:8px;display:block;">` : "";
        const descShort = m.desc ? (m.desc.length>200?m.desc.substring(0,200)+'...':m.desc) : '';
        const popupHtml = `<div style="text-align:left;max-width:260px;">${imgHtml}<strong>${m.name}</strong><p style="font-size:12px;color:#333;margin:8px 0;">${descShort}</p></div>`;
        marker.bindPopup(popupHtml, {maxWidth:280});
        window.appMarkers.push(marker);
    });
}

// initially add all markers
createMarkersFromList(markers);

function addNearbyMarkers(nearbyMonuments){
    if(window.tempMarkers) window.tempMarkers.forEach(m => map.removeLayer(m));
    window.tempMarkers = [];
    if(!nearbyMonuments || nearbyMonuments.length === 0) return;
    const first = nearbyMonuments[0];
    const searchCircle = L.circle([first.lat, first.lon], {
        radius: 50000,
        color: '#ff6b6b',
        fillColor: '#ff6b6b',
        fillOpacity: 0.1,
        weight: 2,
        dashArray: '5,5'
    }).addTo(map);
    window.tempMarkers.push(searchCircle);
    nearbyMonuments.forEach(m => {
        if(!m.lat || !m.lon) return;
        const icon = L.divIcon({
            html: `<div style="background:white;border-radius:50%;padding:4px;display:flex;justify-content:center;align-items:center;box-shadow:0 4px 12px rgba(0,0,0,0.3);border:2px solid #4B0082;">
                    <img src="${m.image || 'https://cdn-icons-png.flaticon.com/512/684/684908.png'}" style="width:36px;height:36px;border-radius:50%;">
                   </div>`,
            className: ''
        });
        const marker = L.marker([m.lat, m.lon], {icon: icon}).addTo(map);
        const descShort = m.desc ? (m.desc.length > 120 ? m.desc.substring(0,120)+'...' : m.desc) : '';
        const popupHtml = `<div style="text-align:center; max-width:180px;"><strong>${m.name}</strong><p style="font-size:12px;color:#333;margin:4px 0;">${descShort}</p></div>`;
        marker.bindPopup(popupHtml, {maxWidth:200});
        window.tempMarkers.push(marker);
    });
    map.setView([first.lat, first.lon], 10);
}

window.addEventListener('message', (e) => {
    if(!e.data) return;
    if(e.data.type === 'addNearby'){
        addNearbyMarkers(e.data.monuments);
    }else if(e.data.type === 'setCity'){
        const city = e.data.city || '';
        if(!city){
            // show all
            createMarkersFromList(markers);
            map.setView([45.94,24.97],7);
        } else {
            const filtered = markers.filter(m => (m.localitate || '').toLowerCase().includes(city.toLowerCase()));
            if(filtered.length>0){
                createMarkersFromList(filtered);
                map.setView([filtered[0].lat, filtered[0].lon], 12);
            } else {
                // no matches -> clear and center
                clearAppMarkers();
            }
        }
    }
});
</script>
</body>
</html>
"""
    f.write(template.replace('{MARKERS}', markers_json))
    
# === Date harta și coordonate ===
lat_max, lat_min = 48.27, 43.63
lon_min, lon_max = 20.26, 29.65
search_radius = 0.5

# Timișoara bounding box (used when the app is in Timisoara view)
# bottom-left = (45.74033907806305, 21.19006057720918)
# top-right   = (45.777135769290304, 21.265946363968798)

TIM_LAT_MIN = 45.74033907806305
TIM_LON_MIN = 21.19006057720918
TIM_LAT_MAX = 45.777135769290304
TIM_LON_MAX = 21.265946363968798
TIM_SEARCH_RADIUS = 0.006

def draw_cloud(draw, cx, cy, text, font):
    # dimensiuni bază
    text_bbox = font.getbbox(text)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    # norul va fi puțin mai mare decât textul
    cloud_w = text_w + 40
    cloud_h = text_h + 30

    # coordonate cercuri puf
    offsets = [(-10,0), (10,0), (0,-5), (-5,-5), (5,-5), (0,5)]
    for dx, dy in offsets:
        r = 15
        draw.ellipse(
            (cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r),
            fill=(255,255,255,220)
        )

    # margine pentru claritate dacă se suprapun
    draw.rounded_rectangle(
        (cx - cloud_w//2, cy - cloud_h//2, cx + cloud_w//2, cy + cloud_h//2),
        radius=20, outline=(150,150,150,180), width=2
    )

    # scriem textul în mijloc
    draw.text((cx, cy), text, font=font, fill=(0,0,0,255), anchor="mm")


def draw_markers_on_image(evt: gr.SelectData, img_input):
    if evt is None:
        return "No click detected", Image.open("assets/harta_romaniei.jpg"), []

    if isinstance(img_input, np.ndarray):
        img = Image.fromarray(img_input).convert("RGBA")
    elif isinstance(img_input, str):
        img = Image.open(img_input).convert("RGBA")
    else:
        img = img_input.convert("RGBA")

    draw = ImageDraw.Draw(img)
    w, h = img.size
    x_px, y_px = evt.index

    # decide which coordinate bounds and dataset to use based on global view
    is_tm = False
    try:
        is_tm = app_settings.is_timisoara()
    except Exception:
        is_tm = False

    if is_tm:
        lat_min_loc, lat_max_loc = TIM_LAT_MIN, TIM_LAT_MAX
        lon_min_loc, lon_max_loc = TIM_LON_MIN, TIM_LON_MAX
        radius_use = TIM_SEARCH_RADIUS
        dataset_path = "datasets/dataset_timisoara.xml"
    else:
        lat_min_loc, lat_max_loc = lat_min, lat_max
        lon_min_loc, lon_max_loc = lon_min, lon_max
        radius_use = search_radius
        dataset_path = 'datasets/dataset.xml'

    # convert pixel -> lat/lon using the selected bounds
    lat = lat_max_loc - y_px * (lat_max_loc - lat_min_loc) / h
    lon = lon_min_loc + x_px * (lon_max_loc - lon_min_loc) / w

    nearby = []
    for m in load_monuments(dataset_path):
        if m.get("lat") is None or m.get("lon") is None:
            continue
        if abs(m["lat"] - lat) <= radius_use and abs(m["lon"] - lon) <= radius_use:
            nearby.append(m)

    if not nearby:
        print(f"[CLICK] Mode: {'Timisoara' if is_tm else 'Romania'}; Click: ({lat:.5f}, {lon:.5f}) - 0 monumente")
        return (f"Click: ({lat:.5f}, {lon:.5f}) - 0 monumente", img, gr.update(choices=[], value=[]))

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    # centrul clusterului (compute using the same bounds selected above)
    mx_center = int(np.mean([(m["lon"] - lon_min_loc) / (lon_max_loc - lon_min_loc) * w for m in nearby]))
    my_center = int(np.mean([(lat_max_loc - m["lat"]) / (lat_max_loc - lat_min_loc) * h for m in nearby]))

    n = len(nearby)
    radius = 0 if n == 1 else min(40 + 15*n, 90)  # dacă e un singur monument, rămâne pe loc, altfel cerc mai mare

    for i, m in enumerate(nearby):
        angle = 2 * math.pi * i / n
        mx = int(mx_center + radius * math.cos(angle))
        my = int(my_center + radius * math.sin(angle))

        text = m["nume"]
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad_x, pad_y = 15, 10
        cloud_w, cloud_h = text_w + pad_x*2, text_h + pad_y*2

        draw.rounded_rectangle(
            (mx - cloud_w//2, my - cloud_h//2, mx + cloud_w//2, my + cloud_h//2),
            radius=10,
            fill=(255,255,255,230)
        )

        draw.text((mx, my), text, font=font, fill=(0,0,0,255), anchor="mm")

    nearby_names = [m["nume"] for m in nearby]
    print(f"[CLICK] Mode: {'Timisoara' if is_tm else 'Romania'} | Click: ({lat:.5f}, {lon:.5f}) - {len(nearby)} monumente")
    return f"Click: ({lat:.5f}, {lon:.5f}) - {len(nearby)} monumente", img, gr.update(choices=nearby_names, value=[])

# === Procesare monument UI existent ===
def process_monument_ui(monument_name):
    # pick dataset according to current global view
    try:
        is_tm = app_settings.is_timisoara()
    except Exception:
        is_tm = False

    dataset_path = "datasets/dataset_timisoara.xml" if is_tm else None

    # look up the monument in the appropriate dataset (substring, case-insensitive)
    monument = None
    for m in load_monuments(dataset_path):
        if m.get("nume") and monument_name.lower() in m.get("nume").lower():
            monument = m
            break

    # fallback to global matcher if not found
    if monument is None:
        monument = match_monument_by_name(monument_name)

    caption = monument.get("descriere", "")
    image = None
    if monument.get("image"):
        # images in the datasets are stored relative to the dataset folder
        image = os.path.join("datasets", monument.get("image"))
    music_path = generate_music(caption, output_path="assets/generated_music.wav")
    return caption, music_path, image

# === Coordonate România ===
lat_max, lat_min = 48.27, 43.63
lon_min, lon_max = 20.26, 29.65
search_radius = 0.25

with gr.Blocks(css="body {background: linear-gradient(to right,#f0f4ff,#d9e4ff);} .card {border-radius:15px;box-shadow:0 8px 20px rgba(0,0,0,0.18);padding:12px;}") as demo:
    gr.Markdown("<h1 style='text-align:center;color:#4B0082;'>🎵 Monument History AI — Harta Interactivă</h1>")

    gr.Markdown("### 🖱️ Click pe harta statică pentru coordonate")
    gr.Markdown("Apasă un marker pe hartă sau click pe harta statică pentru coordonate.")
    click_img = gr.Image(value="assets/harta_romaniei.jpg", interactive=True)
    click_output = gr.Textbox(label="Coordonate click", interactive=False, lines=2)
    monument_dropdown = gr.Dropdown(choices=monuments_list, label="Selectează monument")
    generate_btn = gr.Button("🎶 Generează muzică")
    # hidden bridge HTML to send messages to iframe when updated
    bridge_out = gr.HTML("", visible=False)
    # state to keep track of current view: 'ro' or 'tm'
    view_state = gr.State(value='ro')
    toggle_city_btn = gr.Button("Toggle Timișoara view")
    
    with gr.Row():
        with gr.Column(scale=2):
            # map iframe that can be controlled via postMessage
            map_iframe = gr.HTML(f"<iframe id='mapframe' src='{map_html_path}' width='100%' height='480' style='border:none;border-radius:12px;'></iframe>")
            image_card = gr.Image(label="Imagine monument", type="filepath")
        with gr.Column():
            music_out = gr.Audio(label="Muzică generată", autoplay=True)
            
    caption_out = gr.Textbox(label="Descriere generată", interactive=False, lines=3, max_lines=12, autoscroll=True)
    
    def handle_click(evt: gr.SelectData):
        if evt is None:
            return "No click detected", []
        x_px, y_px = evt.index
        # pick image and bounds according to current global view
        try:
            is_tm = app_settings.is_timisoara()
        except Exception:
            is_tm = False

        img_path = "assets/harta_timisoara.jpg" if is_tm and os.path.exists("assets/harta_timisoara.jpg") else "assets/harta_romaniei.jpg"
        img = Image.open(img_path)
        w, h = img.size
        x, y = x_px / w, y_px / h

        if is_tm:
            lat_min_loc, lat_max_loc = TIM_LAT_MIN, TIM_LAT_MAX
            lon_min_loc, lon_max_loc = TIM_LON_MIN, TIM_LON_MAX
            radius_use = TIM_SEARCH_RADIUS
            dataset_path = "datasets/dataset_timisoara.xml"
        else:
            lat_min_loc, lat_max_loc = lat_min, lat_max
            lon_min_loc, lon_max_loc = lon_min, lon_max
            radius_use = search_radius
            dataset_path = None

        lat = lat_max_loc - y * (lat_max_loc - lat_min_loc)
        lon = lon_min_loc + x * (lon_max_loc - lon_min_loc)

        nearby_monuments = []
        for m in load_monuments(dataset_path):
            if m.get("lat") is None or m.get("lon") is None:
                continue
            if abs(m["lat"] - lat) <= radius_use and abs(m["lon"] - lon) <= radius_use:
                nearby_monuments.append(m)
        nearby_names = [m["nume"] for m in nearby_monuments]
        mode_name = "Timișoara" if is_tm else "Romania"
        print(f"[CLICK] Mode: {mode_name} | Click: ({lat:.5f}, {lon:.5f}) — {len(nearby_monuments)} monumente")
        return f"Click: ({lat:.5f}, {lon:.5f}) — {len(nearby_monuments)} monumente", gr.update(choices=nearby_names, value=[])
    def toggle_city(state):
        """Toggle between Romania map and Timisoara map. Returns (image_path, dropdown_update, bridge_html, new_state)"""
        # find timisoara monuments
        mons = [m for m in load_monuments() if m.get('localitate') and 'timis' in m.get('localitate','').lower()]
        tim_names = [m['nume'] for m in mons]

        # paths
        rom_img = 'assets/harta_romaniei.jpg'
        tm_img = 'assets/harta_timisoara.jpg'
        img_path = rom_img
        new_state = 'ro'
        bridge_js = ''

        if state == 'ro':
            # switch to timisoara
            if os.path.exists(tm_img):
                img_path = tm_img
            else:
                img_path = rom_img
            new_state = 'tm'
            # send setCity message to iframe to filter markers
            bridge_js = "<script>const f=parent.document.getElementById('mapframe'); if(f) f.contentWindow.postMessage({\"type\":\"setCity\",\"city\":\"Timișoara\"}, '*');</script>"
            dd_update = gr.update(choices=tim_names, value=[])
        else:
            # switch back to romania
            img_path = rom_img
            new_state = 'ro'
            bridge_js = "<script>const f=parent.document.getElementById('mapframe'); if(f) f.contentWindow.postMessage({\"type\":\"setCity\",\"city\":\"\"}, '*');</script>"
            dd_update = gr.update(choices=monuments_list, value=[])

        # update global view setting (make sure to set before returning)
        try:
            app_settings.set_view(new_state)
        except Exception:
            pass

        return img_path, dd_update, bridge_js, new_state

    click_img.select(fn=handle_click, inputs=None, outputs=[click_output, monument_dropdown])

    # Select click pe imagine -> norisori vizibili direct
    click_img.select(
        fn=draw_markers_on_image,
        inputs=[click_img],
        outputs=[click_output, click_img, monument_dropdown]
    )

    generate_btn.click(
        fn=process_monument_ui,
        inputs=[monument_dropdown],
        outputs=[caption_out, music_out, image_card]
    )

    # wire toggle button
    toggle_city_btn.click(fn=toggle_city, inputs=[view_state], outputs=[click_img, monument_dropdown, bridge_out, view_state])

    # client side bridge: forward Gradio dropdown changes (nearby monuments) to the iframe
    js_bridge = f"""
    <script>
    const iframe = document.getElementById('mapframe');
    document.addEventListener('gradio:input_changed', (evt) => {{
        if(!iframe) return;
        const target = evt.target;
        if(target && target.tagName === 'SELECT'){{
            const opts = Array.from(target.selectedOptions || []).map(o => o.value);
            const monuments = opts.map(n => {{ return {{ name: n }} }});
            iframe.contentWindow.postMessage({{type:'addNearby', monuments}}, '*');
        }}
    }});
    </script>
    """
    gr.HTML(js_bridge)

demo.launch(allowed_paths=["."])
