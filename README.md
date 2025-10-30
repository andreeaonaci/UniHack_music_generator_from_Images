# 🏛️ Monument History AI

## Descriere

**Monument History AI** este o aplicație interactivă care combină vizualizarea hărților cu generarea de conținut AI. Utilizatorii pot:

- Vizualiza monumente istorice din România pe hartă sau pe o hartă statică.
- Vizualiza informații și imagini pentru fiecare monument.
- Genera muzică inspirată de descrierea monumentului.
- Afișa markere „norișor” vizibile cu numele monumentelor atunci când se face click pe hartă.

Tehnologii folosite: **Python**, **Gradio**, **Leaflet.js**, **Pillow**, **NumPy**.
Scopul proiectului este de a oferi o experiență interactivă și educativă pentru explorarea patrimoniului cultural din România.

---

## Funcționalități

1. **Harta interactivă cu Leaflet**
   - Marker-e pentru fiecare monument încărcat din dataset.
   - Popup-uri cu imagine și descriere scurtă.
   - Cercuri și markere „norișor” pentru monumentele apropiate.

2. **Click pe hartă statică**
   - Imaginea hărții României (`assets/harta_romaniei.jpg`) folosită pentru afișare.
   - Desenează cercuri roșii semi-transparente și text clar deasupra monumentelor.
   - Actualizează imaginea în timp real în frontend.

3. **Generare de conținut AI**
   - Pentru fiecare monument selectat:
     - **Caption**: descriere generată automat.
     - **Muzică**: fișier `.wav` generat pe baza descrierii, dinamic, la rularea aplicației.
     - **map.html** - hartă Leaflet generată automat la rulare.

4. **Dataset**
   - Include: nume, latitudine, longitudine, descriere, imagine.
   - Marker-ele sunt construite automat pe baza datelor, afișând monumentele din zona selectată.

---

## Structura proiectului
```
project_root/ 
│
├─ app.py # Codul principal al aplicației Gradio + Leaflet
├─ modules/
│ └─ music_generator.py # Funcția generate_music
├─ datasets/
│ └─ monuments.py # Funcții load_monuments și match_monument_by_name
├─ assets/
│ ├─ harta_romaniei.jpg # Harta statică
│ └─ generated_music.wav # Fișier generat
└─ README.md
```

---

## Instalare

1. Creează un mediu virtual și instalează dependențele:

```
conda create -n env_unihack python=3.10
conda activate env_unihack
pip install gradio pillow numpy
```

Asigură-te că ai fișierele din assets/ și modulele modules/music_generator.py și datasets/monuments.py.

2. Rulează aplicația:

``` 
python app.py
```

Deschide link-ul afișat de Gradio în browser.

### Exemple de utilizare

- Selectează un monument din dropdown → Apasă 🎶 Generează muzică.

- Click pe hartă → Marker-ele „norișor” apar peste imaginea hărții și afișează numele monumentelor apropiate.

- Ascultă muzica generată și vezi descrierea în timp real.


### Funcții principale

- load_monuments() — încarcă lista monumentelor.

- match_monument_by_name(name) — returnează datele unui monument după nume.

- generate_music(caption) — generează fișier .wav pe baza caption-ului.

- draw_markers_on_image(evt) — desenează cercuri și text peste harta statică când dai click.

- handle_click(evt) — calculează coordonatele click-ului și găsește monumentele apropiate.


