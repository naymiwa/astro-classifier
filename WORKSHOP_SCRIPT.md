# ASTROML Workshop — Slide Copy + Speaker Script

**Talk:** Astronomical Image Simulation & Its Connection to AI
**Speaker:** Nayla A. Argia
**Live demo:** https://lumora-qlpx.onrender.com/

For each slide you get two things:
- **ON SLIDE** — the short text to put on the slide (keep slides light).
- **SAY** — what you speak out loud (your practice script).

> Reminder for slides 6, 11, 13, 14: delete the leftover Canva template text
> (the "Juliana Silva / Aerospace", "ISS Moves at 28,000 km/h", "Aircraft Cruise
> at 35,000 Feet" boxes). Replace with the copy below.

---

## Slide 1 — Title

**ON SLIDE (already good):**
- ASTRONOMICAL IMAGE SIMULATION
- & ITS CONNECTION TO AI
- Nayla Argia

**SAY:**
"Good morning everyone, and welcome. My name is Nayla. For the next session
we're going to do something that sounds impossible at first: we'll create real
astronomical images of stars and galaxies without a telescope, using just a few
lines of Python. Then we'll feed those images into an AI that tells us what
they are. By the end, every one of you will have built your own synthetic sky
and tested it on a live web app. Let's get started."

---

## Slide 2 — The Hook

**ON SLIDE (already good):**
- WHAT IF YOU CAN'T ACCESS A TELESCOPE WHENEVER YOU WANT?

**SAY:**
"Here's the real problem astronomers face. Telescope time is scarce and
expensive. The biggest observatories are booked months in advance, weather
ruins observing nights, and space telescopes like Hubble get far more requests
than they can ever grant. So what do you do when you need an image of a star or
a galaxy right now, and you simply can't point a telescope at the sky?"

---

## Slide 3 — The Solution

**ON SLIDE (already good):**
- WHAT IF YOU CAN'T ACCESS A TELESCOPE WHENEVER YOU WANT?
- SOLUTION: BUILD THE IMAGE YOURSELF, SYNTHETICALLY

**SAY:**
"The answer is simulation. Instead of capturing light, we describe the object
with mathematics and let the computer draw it for us. Astronomers do this every
day: they generate synthetic images to test their instruments, plan
observations, and, as we'll see at the end, to train artificial intelligence.
Today, you become the observatory."

---

## Slide 4 — About Me
*(Replace the "Juliana Silva / Aerospace Systems Engineer" template text.)*

**ON SLIDE:**
- Nayla A. Argia
- Software Engineering student
- Suggested one-liner: "I build software and I love astronomy, so this workshop
  sits right where both meet: code that creates the cosmos."

**SAY:**
"A quick word about me. I'm Nayla, a Software Engineering student. This project
is where my two interests meet, writing code and exploring astronomy. I built
the web app you'll use later, and I'll show you exactly how it works. You don't
need an astronomy or a coding background today; if you can copy, paste, and run,
you can do everything in this session."

---

## Slide 5 — Today's Agenda
*(Fill the "text here" placeholders.)*

**ON SLIDE:**
1. **Core Concepts & Overview** — What we're imaging: stars, galaxies, nebulae, constellations, and why we simulate them.
2. **The Math Behind the Image** — Two simple models: Gaussian for stars, Sérsic for galaxies.
3. **Hands-On Coding** — Run the Python (Astropy) generator in Google Colab.
4. **Visualization in SAOImage DS9** — Open your FITS file and color it like a real astronomer.
5. **Web Demo (the surprise)** — Upload your creation to an AI classifier and see it get recognized.

**SAY:**
"Here's our roadmap. First, the concepts, what these objects actually are.
Second, the math, and don't worry, it's just two formulas. Third, you write and
run the code yourselves in Google Colab. Fourth, we open your image in a
professional astronomy tool called DS9 and make it colorful. And finally, the
surprise at the end: you'll upload your own image to an AI that classifies it.
Roughly five parts, mostly hands-on."

---

## Slide 6 — Galaxies
*(Replace the "engines that power aircraft" leftover box.)*

**ON SLIDE:**
- **GALAXY** — A massive, gravitationally bound system of stars, gas, dust, and dark matter. Galaxies hold anywhere from millions to hundreds of billions of stars.

**GALAXY TYPES (Hubble sequence):**
- **Spiral (Sa, Sb, Sc):** A flat, rotating disk with spiral arms and active star formation. *Example: Andromeda (M31).*
- **Elliptical (E0–E7):** Smooth, rounded, mostly older stars, little new star formation.
- **Lenticular (S0) & Irregular:** In-between disks without clear arms (S0), or no regular shape at all (irregular), often shaped by collisions.

**SAY:**
"Let's meet our objects, starting with galaxies. A galaxy is a huge collection
of stars, gas, dust, and dark matter, all held together by gravity, from
millions of stars up to hundreds of billions. Astronomers sort them by shape.
Spirals, like our neighbor Andromeda, have those beautiful arms and are still
forming new stars. Ellipticals are smooth and rounded, made mostly of older
stars. And then there are the in-between and irregular ones. Keep the spiral
shape in mind, because when we simulate a galaxy, we're going to recreate that
smooth, spread-out glow with math."

---

## Slide 7 — Nebula

**ON SLIDE:**
- **NEBULA** — A giant cloud of gas and dust in space. Some are the birthplaces of new stars; others are the glowing remains of dying ones.
- Types: emission, reflection, dark, planetary, and supernova remnants.
- *source: Hubble Space Telescope*

**SAY:**
"Next, nebulae. A nebula is an enormous cloud of gas and dust. Some are stellar
nurseries where gravity pulls the gas together to ignite brand-new stars. Others
are the opposite, the glowing wreckage of a star that has died. The famous
colorful Hubble images you've probably seen, the Pillars of Creation for
example, are nebulae. They're some of the most photogenic objects in the sky."

---

## Slide 8 — Constellation

**ON SLIDE:**
- **CONSTELLATION** — A recognizable pattern of stars as seen from Earth. The International Astronomical Union officially recognizes **88** constellations that map the entire sky.
- Note: the stars in a pattern are usually **not** close together in space; they only *look* aligned from our point of view.

**SAY:**
"A constellation is a pattern, think Orion or the Big Dipper. Officially there
are 88 of them, and together they act like a map that divides the whole sky into
regions. Here's the interesting part: the stars in a constellation usually
aren't neighbors at all. They can be hundreds of light-years apart; they just
happen to line up from where we stand on Earth. A constellation is really about
perspective."

---

## Slide 9 — Star

**ON SLIDE:**
- **STAR** — A luminous sphere of plasma held together by its own gravity, powered by nuclear fusion in its core. Stars are the fundamental building blocks of galaxies.
- In an image, a single star is essentially a **point of light** spread slightly by the telescope, this is the key fact we'll simulate.
- *source: NASA images*

**SAY:**
"And finally, the star, the object we'll simulate first. A star is a giant ball
of plasma fusing elements in its core, which is what makes it shine. Here's the
one fact that matters for us today: a star is so far away that it's basically a
single point of light. When a telescope captures it, that point gets slightly
blurred into a small round dot. Remember that word, blur, because in a few
minutes we'll recreate exactly that blur with a bell-curve formula."

---

## Slide 10 — Context of Image Simulation

**ON SLIDE:**
- **CONTEXT OF IMAGE SIMULATION**
- Simulation = describe the object with math, then render it as an image, no telescope needed.
- Why it matters: test instruments, plan observations, and generate labelled data to train AI.

**SAY:**
"So what exactly is image simulation? Simple: instead of collecting light, we
describe an object mathematically and let the computer paint the picture. We
control everything, position, size, brightness, shape. Astronomers rely on this
to test their cameras before a mission, to plan what an observation will look
like, and, crucially for us, to create labelled training data for AI. Let's look
at why that's such a big deal."

---

## Slide 11 — Why Mock Images?
*(Replace ALL the ISS / aircraft template text.)*

**ON SLIDE:**
- **WHY DO ASTRONOMERS NEED TO MOCK IMAGES?**
- **Telescope time is limited** — Real data is scarce, expensive, and weather-dependent. Simulation is unlimited and free.
- **Perfect ground truth** — You already know if it's a star or a galaxy, so it's ideal for training and testing algorithms.
- **The FITS format** — Simulated images are saved as FITS (Flexible Image Transport System), the universal standard astronomers have used for decades. It stores the raw pixel data *plus* a header of metadata, and it's what real observatories and space telescopes produce.

**SAY:**
"Why go to the trouble of faking an image? Three reasons. First, real telescope
data is scarce and expensive; a simulation costs nothing and you can make
thousands. Second, and this is the killer feature, you already know the answer.
When you generate a galaxy, it is a galaxy, by definition. That perfect,
guaranteed label is exactly what you need to train and test software. Third, we
save these in a format called FITS, the Flexible Image Transport System. FITS is
the standard astronomers have used for decades: it holds the pixel values plus a
header full of metadata, and it's the very same format Hubble and professional
observatories produce. So the file you make today is structurally identical to a
real observation."

---

## Slide 12 — The Mathematical Bridge

**ON SLIDE:**
- **THE MATHEMATICAL BRIDGE** — Two formulas turn numbers into astronomical objects.

- **GAUSSIAN 2D → a STAR**
  A 2D bell curve: bright at the center, fading outward. This mimics how a telescope blurs a point of light (the "point spread function").
  Parameters: amplitude · x_mean, y_mean (position) · standard deviation (width) · theta (rotation)

- **SÉRSIC MODEL → a GALAXY**
  Describes how a galaxy's brightness falls off from its center, giving that smooth, extended glow.
  Parameters: amplitude · effective radius (r_eff) · Sérsic index (n) · ellipticity · theta

**SAY:**
"Here's the bridge between math and astronomy, and it's only two formulas.

For a star, we use a two-dimensional Gaussian, a bell curve. It's brightest in
the middle and fades out smoothly in every direction. That's a near-perfect
description of how a telescope spreads a single point of starlight, something
astronomers call the point spread function. We control its position, its width,
and its brightness.

For a galaxy, we use the Sérsic model. Instead of a sharp point, it describes a
soft, extended glow that fades gradually from a bright core. Two knobs matter
most: the effective radius, how big it is, and the Sérsic index, which controls
how concentrated the light is. A low index looks like a spiral disk; a high
index looks like a dense elliptical.

That's the whole secret. A tight bell curve is a star. A broad, smooth profile
is a galaxy. Now let's build them."

---

## Slide 13 — Hands-On: Coding & Visualization
*(Replace the ISS template lines.)*

**ON SLIDE:**
- **CODING & VISUALIZATION**
1. **Open the Google Colab template** — no installation, it runs in your browser.
2. **Write your code** — build a star with `Gaussian2D`, a galaxy with `Sersic2D`, and save each as its own FITS file.
3. **Make it colorful in DS9** — open your FITS in SAOImage DS9 and apply a color map to reveal the structure, just like a professional astronomer.

**SAY (walk them through it live):**
"Now it's your turn. Open the Colab link, you don't install anything, it runs in
the browser. We'll go cell by cell together.

First we import our tools, NumPy for the numbers and Astropy for the models.
Then we create a blank 300-by-300 canvas. For the star, we call Gaussian2D and
place a nice tight, bright dot. For the galaxy, we call Sérsic2D with a bigger
radius and a higher index so it spreads out into that soft glow. Then we save
each one as its own FITS file, one star file, one galaxy file, separately.

Once you have your FITS files, we open them in DS9. Right now it looks gray and
flat. Watch what happens when I pick a color map and adjust the scale, suddenly
you can see the structure. That's exactly what astronomers do to bring an image
to life. Take a few minutes, experiment with the parameters, and make it yours."

> **Important to say out loud:** "Save the star and the galaxy as *separate*
> files. Don't combine them into one image, the AI at the end expects exactly
> one object per file, just like a real telescope cutout."

---

## Slide 14 — Connecting Synthetic Data to ML & AI
*(Replace ALL the ISS / aircraft template text.)*

**ON SLIDE:**
- **CONNECTING SYNTHETIC DATA TO ML & AI**
- **AI learns from examples** — A classifier only gets good if it sees thousands of labelled images. Real, hand-labelled astronomy data is hard to get.
- **Synthetic data solves it** — Every image you generate comes with a guaranteed label (star or galaxy), so you can produce a huge, perfectly-labelled training set on demand.
- **From your code to a real model** — The exact same Gaussian and Sérsic models you just ran were used to generate the data that trained the classifier you're about to try.

**SAY:**
"So how does all of this connect to AI? An AI image classifier learns by
example, it needs to see thousands of labelled pictures before it can tell a
star from a galaxy. But collecting and hand-labelling that many real telescope
images is slow and expensive.

This is where everything clicks together. The synthetic images we just made come
with a built-in, perfect label. So we can generate as many as we want and train
a model on them. In fact, the very same Gaussian and Sérsic formulas you ran a
minute ago are what produced the training data behind the app I'm about to show
you. You've basically just built a tiny piece of an AI pipeline without
realizing it."

---

## Slide 15 — Live Demo: Your Observatory

**ON SLIDE (already good):**
- LET'S LOOK AT YOUR OBSERVATORY!
- https://lumora-qlpx.onrender.com/

**SAY:** *(see the full Demo Script section below)*
"And here's the payoff. This is Lumora, a web app I built. Let's upload the FITS
file you just created and let the AI classify it."

---

## Slide 16 — How I Built This / Impact
*(Fill "10× growth" and "explanation about how I made this website".)*

**ON SLIDE:**
- **HOW I BUILT LUMORA**
- **Frontend:** a clean single-page web interface (HTML/CSS/JavaScript).
- **Backend:** a Python API (FastAPI) that receives your image and runs the models.
- **The AI:** two deep-learning models, one classifies photos into 6 categories (galaxies, stars, nebulae, planets, constellations, deep space); a second classifies FITS files as star vs galaxy.
- **The data:** trained on synthetic images made with the exact Gaussian + Sérsic method from this workshop.
- **Bonus feature:** after a prediction, generate a shareable "Cosmic Card" of your result.

**SAY:**
"Quickly, how is this built, in case you want to make your own. The part you see
is a simple web page. Behind it is a Python server that receives your image and
passes it to the AI. There are actually two models: one sorts regular photos
into six categories, and a second one specializes in FITS files, deciding star
versus galaxy. And that FITS model, as I said, learned from data made with the
same two formulas you used today. Full circle, from a math equation, to a FITS
file, to an AI that recognizes it."

---

## Slide 17 — Closing / Thank You

**ON SLIDE:**
- THANK YOU
- Try it yourself: https://lumora-qlpx.onrender.com/
- Nayla A. Argia
- (optional) your LinkedIn / Instagram @naylargia

**SAY:**
"That's the whole journey: from 'I don't have a telescope' to 'I built my own
image and an AI recognized it.' The link stays live, so keep experimenting,
change the parameters, break things, and see what the classifier says. Thank you
all so much for coding the cosmos with me today. I'm happy to take any
questions."

---

# FULL DEMO SCRIPT (Slide 15)

### Before the session (do this ~5 minutes before you start the demo)
Your app is hosted on Render's free tier, which "sleeps" after ~15 minutes of no
activity and takes 30–60 seconds to wake up.
1. **~5 minutes before the demo**, open https://lumora-qlpx.onrender.com/ once
   and wait for it to fully load. This wakes the server.
2. Keep the tab open. If there's a long gap before you reach slide 15, refresh
   it once so it doesn't fall back asleep.
3. Have **two FITS files ready** on your machine: one clear `star_image.fits`
   and one clear `galaxy_image.fits` (the ones saved in the Colab notebook,
   Step-7). Also keep a normal **space photo (JPG/PNG)** handy to show the
   6-class image mode.

### Live walkthrough (what to click + what to say)

**1. Open the site.**
"This is Lumora. Think of it as your pocket observatory. It takes an image and
tells you what kind of object it is."

**2. Upload the galaxy FITS file.**
- Click the upload area → choose `galaxy_image.fits`.
"I'm uploading the galaxy I made in Colab a few minutes ago, the same Sérsic
model we ran together."
- Click **Analyze**.
"The app reads the FITS file, renders a preview, and runs it through the AI."

**3. Read the result out loud.**
"And there it is, it's classified as a **galaxy**, with the confidence score
right here. The AI has never seen *this specific* file, but because it was
trained on images made the same way, it recognizes the pattern."

**4. Now upload the star FITS file** and Analyze.
"Let's test the other one, my star. Same pipeline... and it comes back as a
**star**. Notice how different the two look: the star is a tight point, the
galaxy is a broad glow, exactly the difference we built with math."

**5. (Optional) Show the 6-class image mode** with a normal space photo.
"It also handles ordinary astronomy photos. Let me drop in a picture... and it
sorts it into one of six categories, galaxies, stars, nebulae, planets,
constellations, or deep space."

**6. (Optional) Cosmic Card.**
"One fun extra, after a prediction you can generate a shareable 'Cosmic Card'
of your result, like a collectible for your classification. Download it as an
image and post it."

**7. Hand it to the audience.**
"The link is on the screen, please try it right now with the files you just
made. Upload your star, upload your galaxy, and see if the AI agrees with you."

### If something goes wrong (backup plan)
- **Page is slow / spinning:** "This is the free server waking up, give it about
  30 seconds." Keep talking; it will load.
- **A star gets called a galaxy (or vice versa):** stay confident, it's a
  teaching moment. "Great example, the AI isn't perfect. If your object is very
  spread out or has odd edges, it can look ambiguous, which is exactly why
  astronomers care about realistic training data. This is the honest reality of
  machine learning." Then upload a cleaner file that classifies correctly.
- **Upload fails entirely:** have a **screenshot or short screen recording** of a
  successful run saved offline, and show that instead.
- **Tip:** upload files with clean, well-separated single objects; avoid images
  with many stars or objects touching the frame edge, those are genuinely hard
  for a single-object classifier.

---

# TIMING CHEAT SHEET (~45–60 min)
| Section | Slides | Time |
|---|---|---|
| Intro + hook | 1–3 | 4 min |
| About me + agenda | 4–5 | 3 min |
| The objects (galaxy, nebula, constellation, star) | 6–9 | 8 min |
| Why simulate + FITS | 10–11 | 5 min |
| The math (Gaussian + Sérsic) | 12 | 5 min |
| **Hands-on coding + DS9** | 13 | 15–20 min |
| Connect to AI | 14 | 4 min |
| **Live demo** | 15 | 8 min |
| How I built it + close | 16–17 | 5 min |

---

# QUICK FACT-CHECK (so you can answer questions confidently)
- **FITS** = Flexible Image Transport System; the long-standing standard format
  in astronomy; stores an N-dimensional data array plus a human-readable header
  of metadata keywords. Used by NASA, ESA, and observatories worldwide.
- **Point Spread Function (PSF):** how an imaging system spreads a point of
  light. A star is effectively a point source, so its image ≈ the PSF, which is
  well approximated by a 2D Gaussian.
- **Gaussian width ↔ FWHM:** FWHM ≈ 2.355 × standard deviation. (Your notebook's
  stddev = 5 px → FWHM ≈ 11.8 px.)
- **Sérsic index n:** controls light concentration. n ≈ 1 → exponential disk
  (spiral-like); n ≈ 4 → de Vaucouleurs profile (elliptical-like). Your notebook
  uses n = 5, a very concentrated, elliptical-style galaxy.
- **Hubble sequence:** the classic galaxy classification, spiral, elliptical,
  lenticular (S0), and irregular.
- **88 constellations** are officially recognized by the International
  Astronomical Union (IAU).
- **Andromeda (M31):** the nearest large spiral galaxy, ~2.5 million light-years
  away.
- **DS9 (SAOImage DS9):** a professional FITS image viewer from the Smithsonian
  Astrophysical Observatory; lets you apply color maps and brightness scaling.
- **Synthetic (mock) data in ML:** widely used when real labelled data is scarce
  or expensive; its main advantage is perfect, guaranteed ground-truth labels.
