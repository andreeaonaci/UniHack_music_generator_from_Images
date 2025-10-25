import gradio as gr
from modules.captioner import generate_caption
from modules.music_generator import generate_music
from datasets.monuments import load_monuments, match_monument_by_name
import json 

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
                "desc": m.get("descriere",""),
            })
    return json.dumps(markers)

markers_json = build_markers_json()

def process_monument(monument_name="Bran"):
    """
    1. Caută monumentul în dataset
    2. Obține descrierea → caption
    3. Folosește descrierea ca prompt pentru generare muzică
    """
    monument = match_monument_by_name(monument_name)
    
    # fallback
    caption = monument.get("descriere", "").strip()
    print("Caption is: ", caption)
    if not caption:
        caption = f"{monument_name} este un monument istoric important în România, cu o arhitectură remarcabilă."
    
    # eventual extindere prompt
    # caption_for_music = f"Generați o melodie inspirată de: {caption}"
    
    image_path = "datasets/" + monument.get("image")
    
    music_path = generate_music(caption ,output_path="assets/generated_music.wav")
    
    return caption, music_path, image_path

markers_json = build_markers_json()
monuments_list = [m["nume"] for m in load_monuments()]
imgHtml = ""
map_html = f"""
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<div id="map" style="width:100%; height:480px; border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.15)"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  const markers = {markers_json};
  const map = L.map('map', {{zoomControl: true}}).setView([45.94, 24.97], 7);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom: 19}}).addTo(map);
  const icon = L.icon({{iconUrl: 'https://cdn-icons-png.flaticon.com/512/684/684908.png', iconSize:[28,28], iconAnchor:[14,28], popupAnchor:[0,-28] }});
  markers.forEach(m => {{
    const marker = L.marker([m.lat, m.lon], {{icon}}).addTo(map);
    const imgHtml = m.image ? `<img src="${{m.image}}" style="width:120px;border-radius:8px;margin-bottom:8px;display:block;">` : "";
    const popupHtml = `
      <div style="text-align:left;max-width:260px;">
        ${imgHtml}
        <strong>${{m.name}}</strong>
        <p style="font-size:12px;color:#333;margin:8px 0;">${{m.desc ? m.desc.substring(0,200) + (m.desc.length>200?'...':'') : ''}}</p>
        <button onclick="selectMonument('${{m.name.replace(/'/g, \"\\\\'\")}}')" style="background:#4B0082;color:white;border:none;padding:8px 10px;border-radius:8px;cursor:pointer;">Select</button>
      </div>`;
    marker.bindPopup(popupHtml, {{maxWidth:280}});
  }});

  function selectMonument(name) {{
    window.dispatchEvent(new CustomEvent("selectMonument", {{detail: {{name}}}}));
  }}
</script>
"""

with gr.Blocks(css="""
    body {{background: linear-gradient(to right, #f0f4ff, #d9e4ff);}}
    .card {{border-radius: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.18); padding: 12px;}}
""") as demo:

    gr.Markdown("<h1 style='text-align:center; color:#4B0082;'>🎵 Monument History AI — Harta</h1>")
    with gr.Row():
        with gr.Column(scale=1):
            monument_dropdown = gr.Dropdown(choices=monuments_list, label="Selectează monument")
            generate_btn = gr.Button("🎶 Generează muzică")
            info = gr.Markdown("Apasă un marker pe hartă pentru a selecta un monument.")
        with gr.Column(scale=2):
            map_area = gr.HTML(map_html)
            image_card = gr.Image(label="Imagine monument", type="filepath")
            caption_out = gr.Textbox(label="Caption generat", interactive=False)
            music_out = gr.Audio(label="Muzică generată", autoplay=True)

    # Python function to generate for dropdown selection
    def process_monument_ui(monument_name):
        monument = match_monument_by_name(monument_name)
        caption = monument.get("descriere","")
        image = monument.get("image")
        music_path = generate_music(caption, output_path="assets/generated_music.wav")
        return caption, music_path, image

    generate_btn.click(fn=process_monument_ui, inputs=[monument_dropdown], outputs=[caption_out, music_out, image_card])

    # JS -> Python bridge: when the map dispatches selectMonument event, set the dropdown and click generate
    # We attach a small JS listener that updates Gradio input and triggers the button click
    js_code = """
    <script>
    window.addEventListener('selectMonument', (e) => {
        const name = e.detail.name;
        const selects = document.querySelectorAll('select');

        for (let s of selects) {
            for (let opt of s.options) {
                if (opt.text === name) {
                    s.value = opt.value;
                    s.dispatchEvent(new Event('change'));

                    const btn = document.querySelector('button[title="Generează muzică"]') 
                            || document.querySelector('button');
                    if (btn) btn.click();
                    return;
                }
            }
        }
    });
    </script>
    """

    with gr.Blocks() as demo:
        gr.HTML(js_code)

demo.launch()
