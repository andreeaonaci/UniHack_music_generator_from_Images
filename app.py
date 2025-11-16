import gradio as gr
from modules.music_generator import generate_music
from datasets.monuments import load_monuments, match_monument_by_name
import json, os, re
import time
import requests
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
search_radius = 1

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
    print(dataset_path, "loading monuments for click processing")
    for m in load_monuments(dataset_path):
        if m.get("lat") is None or m.get("lon") is None:
            continue
        if abs(m["lat"] - lat) <= radius_use and abs(m["lon"] - lon) <= radius_use:
            nearby.append(m)

    if len(nearby) == 0:
        return f"Click: ({lat:.5f}, {lon:.5f}) - 0 monumente", img, gr.update(choices=[], value=[])

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
    # generate up to 15s, prefer loopable output
    # kept for backward compatibility: generate music and return caption,image,music
    music_path = generate_music(caption, output_path="assets/generated_music.wav", duration_sec=15, loop=True)
    return caption, music_path, image


def preview_monument(monument_name):
    """Fast preview: return caption and image quickly without generating music."""
    try:
        is_tm = app_settings.is_timisoara()
    except Exception:
        is_tm = False
    dataset_path = "datasets/dataset_timisoara.xml" if is_tm else None

    monument = None
    for m in load_monuments(dataset_path):
        if m.get("nume") and monument_name.lower() in m.get("nume").lower():
            monument = m
            break
    if monument is None:
        monument = match_monument_by_name(monument_name)

    caption = monument.get("descriere", "")
    image = None
    if monument.get("image"):
        image = os.path.join("datasets", monument.get("image"))

    # build image carousel: find images in datasets/images* that contain a slug of the monument name
    def slug(s: str) -> str:
        s = (s or "").lower().strip()
        s = s.replace(' ', '_')
        s = re.sub(r'[^0-9a-z_]', '', s)
        return s

    imgs = []
    # choose folder according to current view
    try:
        is_tm = app_settings.is_timisoara()
    except Exception:
        is_tm = False
    img_dir = os.path.join('datasets', 'images_timisoara' if is_tm else 'images')
    if os.path.isdir(img_dir):
        name_slug = slug(monument.get('nume') or monument_name or '')
        for fname in sorted(os.listdir(img_dir)):
            base = os.path.splitext(fname)[0].lower()
            if name_slug and name_slug in base:
                imgs.append(os.path.join(img_dir, fname))
    # build thumbnails and main preview
    thumbs = []
    originals = imgs[:]
    for i, p in enumerate(originals):
        try:
            t = make_thumbnail(p, i)
            thumbs.append(t)
        except Exception:
            thumbs.append(p)

    # determine main original (prefer the dataset `image` if present)
    main_orig = None
    if image and os.path.exists(image):
        main_orig = image
    elif originals:
        main_orig = originals[0]

    main_preview = None
    if main_orig:
        try:
            main_preview = make_main_preview(main_orig, 0)
        except Exception:
            main_preview = main_orig

    # return caption, main image preview, thumbnails (for gallery), originals (state), initial_index
    return caption, main_preview, thumbs, originals, 0


def generate_music_for_monument(monument_name, loop=True, use_local=False):
    """Generate music (slow) for the selected monument and return the audio file path."""
    try:
        is_tm = app_settings.is_timisoara()
    except Exception:
        is_tm = False
    dataset_path = "datasets/dataset_timisoara.xml" if is_tm else None

    monument = None
    for m in load_monuments(dataset_path):
        if m.get("nume") and (monument_name in m.get("nume")):
            monument = m
            break
    if monument is None:
        monument = match_monument_by_name(monument_name)

    caption = monument.get("descriere", "")
    out_path = "assets/generated_music.wav"
    # generate up to 15s, respect requested looping
    music_path = generate_music(caption, output_path=out_path, duration_sec=10, loop=bool(loop), use_local=bool(use_local))
    return music_path

# === Coordonate România ===
lat_max, lat_min = 48.27, 43.63
lon_min, lon_max = 20.26, 29.65
search_radius = 0.3


# click handler: compute nearby monuments from a click event on the static map image
def handle_click(evt: gr.SelectData):
    if evt is None:
        return "No click detected", []
    x_px, y_px = evt.index
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
    return f"Click: ({lat:.5f}, {lon:.5f}) — {len(nearby_monuments)} monumente", gr.update(choices=nearby_names, value=[])

# Carousel helpers: update image by index (wraps around)
def _set_gallery_index(images, idx):
    if not images:
        return None, 0
    n = len(images)
    idx = int(idx) % n
    return images[idx], idx

def prev_image(images, idx):
    path, new_idx = _set_gallery_index(images, (int(idx) - 1))
    if path is None:
        return None, new_idx
    return make_main_preview(path, new_idx), new_idx

def next_image(images, idx):
    path, new_idx = _set_gallery_index(images, (int(idx) + 1))
    if path is None:
        return None, new_idx
    return make_main_preview(path, new_idx), new_idx

# Helpers to build resized preview and thumbnails
def _ensure_preview_dirs():
    out_main = os.path.join('assets', 'preview_main')
    out_thumbs = os.path.join('assets', 'preview_thumbs')
    os.makedirs(out_main, exist_ok=True)
    os.makedirs(out_thumbs, exist_ok=True)
    return out_main, out_thumbs

def make_main_preview(orig_path, idx=None):
    out_main, _ = _ensure_preview_dirs()
    try:
        im = Image.open(orig_path).convert('RGB')
        im = im.resize((700, 450), Image.LANCZOS)
        name = f"main_{os.path.splitext(os.path.basename(orig_path))[0]}"
        if idx is not None:
            name = f"{name}_{idx}"
        out_path = os.path.join(out_main, name + '.jpg')
        im.save(out_path, quality=85)
        return out_path
    except Exception:
        return orig_path

def make_thumbnail(orig_path, idx=None):
    _, out_thumbs = _ensure_preview_dirs()
    try:
        im = Image.open(orig_path).convert('RGB')
        im = im.resize((200, 164), Image.LANCZOS)
        name = f"thumb_{os.path.splitext(os.path.basename(orig_path))[0]}"
        if idx is not None:
            name = f"{name}_{idx}"
        out_path = os.path.join(out_thumbs, name + '.jpg')
        im.save(out_path)
        return out_path
    except Exception:
        return orig_path

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

# CSS for layout and the "Alte imagini" gallery box
gr_css = gr_css = """
* { font-family: 'Inter', sans-serif; transition: all .25s ease; }
body, .gradio-container { background: #fefcf5; }
#center_col, .gradio-container .gr-box, .gradio-container .gr-panel { background: rgba(255,255,255,0.8); backdrop-filter: blur(12px); border-radius: 16px; box-shadow: 0 6px 18px rgba(100,80,60,0.1); padding: 18px; }
h1 { font-size:42px; font-weight:800; color:#5a4b3a; text-align:center; }
#center_image { border-radius: 12px; box-shadow: 0 4px 12px rgba(80,60,40,0.15); }
button { border-radius: 10px; background: #c3a66d; color: #fff; border: none; padding: 8px 14px; font-size:14px; }
#prev_btn, #next_btn { width: 40px; font-size:18px; padding:4px 6px; }
"""
with gr.Blocks(css=gr_css) as demo:
    gr.Markdown("<h1>🎵 Music AI — Harta Interactivă</h1>")

    # --- Map Interaction ---
    with gr.Column(scale=1):
        # gr.Markdown("### 🖱️ Click pe harta statică pentru coordonate")
        gr.Markdown("Apasă pe harta de mai jos pentru a selecta un monument și a genera muzică inspirată de acesta.")
        toggle_city_btn = gr.Button("Toggle Timișoara / România")
        click_img = gr.Image(
            value="assets/harta_romaniei.jpg",
            elem_id="click_img",
            interactive=False,
            type="filepath",
            show_label=False,
            show_fullscreen_button=False,
            show_download_button=False,
            show_share_button=False,
            mirror_webcam = False,
        )
        click_output = gr.Textbox(label="Coordonate click", interactive=False, lines=2, visible=False)
        monument_dropdown = gr.Dropdown(choices=monuments_list, label="Selectează monument")
        generate_btn = gr.Button("🎶 Music AI — Generează muzică")
        bridge_out = gr.HTML("", visible=False)
        view_state = gr.State(value='ro')

    # --- Main Monument Display ---
    with gr.Column(elem_id="center_col", scale=1):
        with gr.Row(variant="compact", elem_id="carousel_row"):
            prev_btn = gr.Button("◀", elem_id="prev_btn")
            image_card = gr.Image(
                label="main_image",
                type="filepath",
                elem_id="center_image",
                interactive=False,
                show_fullscreen_button=False,
                show_download_button=False,
                show_share_button=False,
                mirror_webcam = False,
                show_label = False,
                scale=8
            )
            next_btn = gr.Button("▶", elem_id="next_btn")

    # --- Image Gallery ---
    image_gallery = gr.Gallery(
        label="gallery",
        show_label=False,
        elem_id="image_gallery",
        columns=4,
        height="100px"
    )

    
    gallery_state = gr.State(value=[])
    gallery_index = gr.State(value=0)

    # --- Music Controls ---
    with gr.Row():
        music_out = gr.Audio(label="Muzică generată", autoplay=True, elem_id="generated_audio")
        with gr.Column():
            loop_checkbox = gr.Checkbox(label="Loop muzică", value=True, elem_id="loop_checkbox")
            use_local_checkbox = gr.Checkbox(label="Use local model (MusicGen)", value=False, elem_id="use_local_checkbox")

    caption_out = gr.Textbox(
        label="Descriere generată",
        interactive=False,
        lines=3,
        max_lines=12,
        autoscroll=True
    )

    # --- CSS for layout ---
    gr.HTML("""
    <style>
    :root {
        --gold: #c2a262;
        --bg: #faf7ef;
    }

    /* Whole app background */
    .gradio-container {
        background: var(--bg) !important;
    }

    /* --- CAROUSEL ROW --- */
    #carousel_row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        padding: 15px 0;
    }

    /* Buttons left/right */
    #prev_btn, #next_btn {
        width: 40px !important;
        height: 40px !important;
        font-size: 22px !important;
        border-radius: 8px !important;
        background: var(--gold) !important;
        color: white !important;
        padding: 0 !important;
        flex-shrink: 0;
    }

    /* Main image card */
    #main_image {
        max-width: 650px !important;
        width: 100% !important;
        height: auto !important;
        border-radius: 18px !important;
        border: 5px solid var(--gold) !important;
    }

    /* --- GALLERY --- */
    /* Gallery sizing: show thumbnails at reasonable size (use generated thumbs) */
    #image_gallery {
        transform: none !important;
        margin-top: 0 !important;
        height: auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        padding: 8px !important;
    }

    /* Grid container inside Gradio gallery (fallback) */
    #image_gallery .grid-container {
        gap: 8px !important;
        justify-items: center !important;
    }

    /* Thumbnails: prefer the generated thumbnail size, keep height half of main (225px) */
    #image_gallery img {
        height: 225px !important;
        width: auto !important;
        object-fit: cover !important;
        border-radius: 10px !important;
        border: 2px solid var(--gold) !important;
    }

    /* --- AUDIO PLAYER + CHECKBOXES MATCH THE THEME --- */
    #generated_audio {
        border-radius: 15px !important;
    }
    </style>
    """)


    # --- Interactions ---
    click_img.select(fn=handle_click, inputs=None, outputs=[click_output, monument_dropdown])
    click_img.select(fn=draw_markers_on_image, inputs=[click_img], outputs=[click_output, click_img, monument_dropdown])

    generate_btn.click(
        fn=preview_monument,
        inputs=[monument_dropdown],
        outputs=[caption_out, image_card, image_gallery, gallery_state, gallery_index],
        queue=False
    ).then(
        fn=generate_music_for_monument,
        inputs=[monument_dropdown, loop_checkbox, use_local_checkbox],
        outputs=[music_out],
        queue=True
    )

    prev_btn.click(fn=prev_image, inputs=[gallery_state, gallery_index], outputs=[image_card, gallery_index])
    next_btn.click(fn=next_image, inputs=[gallery_state, gallery_index], outputs=[image_card, gallery_index])

    toggle_city_btn.click(fn=toggle_city, inputs=[view_state], outputs=[click_img, monument_dropdown, bridge_out, view_state])

    # client side bridge: forward Gradio dropdown changes (nearby monuments) to the iframe
    js_bridge = """
    <script>
    const iframe = document.getElementById('mapframe');

    function setAudioLoopFromCheckbox(){
        try{
            const audio = document.getElementById('generated_audio');
            const chk = document.getElementById('loop_checkbox');
            if(audio) audio.loop = chk ? !!chk.checked : true;
        }catch(e){console.warn('setAudioLoopFromCheckbox error', e);}
    }

    function attachEndedHandler(){
        try{
            const audio = document.getElementById('generated_audio');
            const chk = document.getElementById('loop_checkbox');
            if(!audio) return;
            // remove previous handler if present
            audio.removeEventListener && audio.removeEventListener('ended', audio._loopHandler || (()=>{}));
            const handler = () => {
                try{
                    const doLoop = chk ? !!chk.checked : true;
                    if(doLoop){
                        // restart playback
                        audio.currentTime = 0;
                        const p = audio.play();
                        if(p && p.catch) p.catch(()=>{});
                    }
                }catch(e){/* swallow */}
            };
            audio._loopHandler = handler;
            audio.addEventListener && audio.addEventListener('ended', handler);
        }catch(e){console.warn('attachEndedHandler error', e);}
    }

    document.addEventListener('gradio:input_changed', (evt) => {
        const target = evt.target;
        // forward dropdown (nearby monuments) to iframe
        if(iframe && target && target.tagName === 'SELECT'){
            const opts = Array.from(target.selectedOptions || []).map(o => o.value);
            const monuments = opts.map(n => { return { name: n } });
            iframe.contentWindow.postMessage({type:'addNearby', monuments}, '*');
        }

        // toggle audio loop when the loop checkbox changes
        if(target && target.id === 'loop_checkbox'){
            setAudioLoopFromCheckbox();
        }
    });

    // Ensure the audio element is looped by default on initial load
    window.addEventListener('load', setAudioLoopFromCheckbox);

    // Watch for DOM insertions so we can re-apply loop and re-attach ended handler when Gradio replaces the audio element
    const observer = new MutationObserver((mutations) => {
        for(const m of mutations){
            for(const node of m.addedNodes){
                if(!node) continue;
                if(node.id === 'generated_audio'){
                    setAudioLoopFromCheckbox();
                    attachEndedHandler();
                } else if(node.querySelector){
                    const found = node.querySelector && node.querySelector('#generated_audio');
                    if(found) setAudioLoopFromCheckbox();
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Also attach handler on load in case audio already exists
    window.addEventListener('load', () => { attachEndedHandler(); });
    </script>
    """
    gr.HTML(js_bridge)

# Register a Suno callback on Gradio's FastAPI server so Suno can POST completion data
try:
    from fastapi import Request, BackgroundTasks
    from modules.audio_utils import download_and_convert

    def _bg_process_and_save(items):
        out_dir = os.path.join("assets", "suno_callback")
        os.makedirs(out_dir, exist_ok=True)
        saved = []
        for i, it in enumerate(items):
            audio_url = it.get("audio_url") or it.get("stream_audio_url") or it.get("source_audio_url")
            id_ = it.get("id") or f"suno_{int(time.time())}_{i}"
            if not audio_url:
                continue
            out_path = os.path.join(out_dir, id_ + ".wav")
            try:
                download_and_convert(audio_url, out_path)
                saved.append({"id": id_, "wav": out_path, "audio_url": audio_url})
            except Exception as e:
                print("Error downloading/converting callback audio:", e)
        print("Suno callback background saved:", saved)

    try:
        # Detect the FastAPI/Starlette app object on the Gradio Blocks instance.
        server_app = None
        found_attr = None
        for name in ("server_app", "app", "_app", "app_app", "B_app", "server"):
            candidate = getattr(demo, name, None)
            if candidate is None:
                continue
            # If candidate has a .post decorator (FastAPI/Starlette), use it directly
            if hasattr(candidate, "post"):
                server_app = candidate
                found_attr = name
                break
            # Sometimes Gradio stores the starlette app under demo.server.app
            if name == "server":
                candidate2 = getattr(candidate, "app", None)
                if candidate2 and hasattr(candidate2, "post"):
                    server_app = candidate2
                    found_attr = "server.app"
                    break

        if server_app is None:
            raise RuntimeError(f"Could not locate FastAPI/Starlette app on demo (tried attrs). demo attrs: {', '.join(dir(demo)[:30])}")

        print(f"Registering /suno_callback on demo.{found_attr}")

        @server_app.post("/suno_callback")
        async def suno_callback(request: Request, background_tasks: BackgroundTasks):
            # optional secret header check
            secret = os.getenv("SUNO_CALLBACK_SECRET")
            if secret:
                hdr = request.headers.get("X-Callback-Token") or request.headers.get("x-callback-token")
                if not hdr or hdr != secret:
                    print("Rejected Suno callback: missing/invalid X-Callback-Token header")
                    return {"error": "forbidden"}, 403

            try:
                payload = await request.json()
            except Exception:
                return {"error": "invalid json"}, 400

            # follow the Flask example shape in your message
            code = payload.get('code')
            msg = payload.get('msg')
            callback_data = payload.get('data', {}) or {}
            task_id = callback_data.get('task_id')
            callback_type = callback_data.get('callbackType')
            music_data = callback_data.get('data') or []

            print(f"Received music generation callback: {task_id}, type: {callback_type}, status: {code}, message: {msg}")

            out_dir = os.path.join("assets", "suno_callback")
            os.makedirs(out_dir, exist_ok=True)

            if code == 200:
                print("Music generation completed")
                print(f"Generated {len(music_data)} music tracks:")
                for i, music in enumerate(music_data):
                    print(f"Music {i + 1}:")
                    print(f"  Title: {music.get('title')}")
                    print(f"  Duration: {music.get('duration')} seconds")
                    print(f"  Tags: {music.get('tags')}")
                    print(f"  Audio URL: {music.get('audio_url')}")
                    print(f"  Cover URL: {music.get('image_url')}")

                    # Download audio file synchronously (save as mp3)
                    try:
                        audio_url = music.get('audio_url')
                        if audio_url:
                            r = requests.get(audio_url, stream=True, timeout=60)
                            r.raise_for_status()
                            filename = os.path.join(out_dir, f"generated_music_{task_id}_{i + 1}.mp3")
                            with open(filename, "wb") as fh:
                                for chunk in r.iter_content(8192):
                                    if chunk:
                                        fh.write(chunk)
                            print(f"Audio saved as {filename}")
                    except Exception as e:
                        print(f"Audio download failed: {e}")
            else:
                print(f"Music generation failed: {msg}")
                if code == 400:
                    print("Parameter error or content violation")
                elif code == 451:
                    print("File download failed")
                elif code == 500:
                    print("Server internal error")

            # Return 200 status code to confirm callback received
            return {"status": "received"}

        print("✅ Registered /suno_callback on Gradio server")
    except Exception as e:
        print("Could not register Suno callback on Gradio server:", e)
except Exception:
    pass

demo.launch(allowed_paths=["."])
