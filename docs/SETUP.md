# Setting up your Neo dashboard

> ## 🌐 Did Mariah send you a web link?
> If you got a link like **`https://neo-dashboard-….onrender.com`** plus a
> username and password, **that's all you need.** Open the link, type the
> username and password once, and bookmark it. You can stop reading here —
> the rest of this page is only for running Neo on your own Mac instead.

This is the plain-English guide to getting the Neo dashboard running on your
own Mac. No coding needed — you'll copy a few things and type two commands.

When it's running you get **one page**: type (or speak) a request, Neo drafts
it, and proposals show up under **In Review** for you to **Approve**.

> **Heads up — where the dashboard "lives" (local version):** when you run it
> yourself, Neo runs *on your Mac*. The link you open
> (`http://127.0.0.1:8000`) works **only on this Mac, while the Terminal
> window is open** — it's not reachable from your phone or another computer.
> (The hosted web link above doesn't have that limitation.)

---

## One-time setup

You only do steps 1–5 once.

### 1. Install Python

Neo needs Python (a free program that runs it).

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python** button.
3. Open the downloaded file and click through the installer (Continue →
   Agree → Install). Enter your Mac password if asked.

### 2. Get a GitHub account, then the Neo files

Neo's code lives in a **private** project, so you need a free GitHub account
and Mariah has to invite you.

1. Create a free account at **https://github.com/signup** (skip if you already
   have one). Send Mariah your username — she'll add you to the project, and
   you'll get an email invite to **Accept**.
2. Make sure you're **signed in** at **github.com**, then open
   **https://github.com/mariahdi/neo**.
3. Click the green **`<> Code`** button, then **Download ZIP**.
4. Open your **Downloads** folder and double-click the ZIP to unzip it.
   You'll get a folder called **`neo-main`**.
5. Drag that folder somewhere easy to find — for example, your **Desktop**.

### 3. Open Terminal in the Neo folder

1. Open the **Terminal** app (press `Cmd + Space`, type *Terminal*, hit
   Return).
2. Type `cd ` (the letters c, d, then a space — don't press Return yet).
3. Drag the **`neo-main`** folder from your Desktop onto the Terminal window.
   It will paste the folder's location.
4. Now press **Return**.

You're now "inside" the Neo folder. Every command below happens here.

### 4. Install the parts Neo needs

Type this and press Return (it downloads a few helpers — takes a minute):

```bash
pip3 install -r requirements.txt
```

If that says `pip3: command not found`, use this instead:

```bash
python3 -m pip install -r requirements.txt
```

### 5. Add your keys

Neo needs a small file called **`neo.env`** that holds the passwords for Jira,
GitHub, and the AI. **Mariah will send you this file** — save it directly into
the **`neo-main`** folder (next to the other files).

> Don't share `neo.env` with anyone or post it anywhere — it's like a set of
> house keys.

---

## Starting the dashboard

Do this whenever you want to use Neo. In the Terminal (inside the `neo-main`
folder), type:

```bash
source neo.env && ./run-dashboard.sh
```

You'll see a line like:

```
Starting Neo dashboard on http://127.0.0.1:8000
```

Now open **http://127.0.0.1:8000** in your web browser (Safari or Chrome).
That's your dashboard. **Bookmark it** so it's one click next time.

### Using it

- **Top bar:** type a request — e.g. *"I need a proposal for the Red Cross"* —
  and press **Send**. Or click the **🎙 microphone** and just talk, then press
  Send. Neo opens a ticket and starts drafting.
- **Board:** watch the request move across To Do → In Progress → In Review →
  Done. It refreshes itself every 30 seconds.
- **In Review:** when a draft is ready it appears here with the full text and
  three buttons — **Approve**, **Request Changes**, **Re-prompt**. Read it and
  click.

### Stopping it

Click the Terminal window and press **`Control + C`**. (Closing the Terminal
window also stops it.) The dashboard link will stop working until you start it
again.

---

## Next time (the short version)

Once you've done the one-time setup, each day it's just:

1. Open **Terminal**.
2. `cd ` then drag in the **`neo-main`** folder, press Return.
3. `source neo.env && ./run-dashboard.sh`
4. Open your bookmark (**http://127.0.0.1:8000**).

---

## If something goes wrong

- **`command not found: python3` / `pip3`** — Python didn't install. Redo
  step 1, then close and reopen Terminal.
- **`Permission denied` when running `./run-dashboard.sh`** — type this once:
  `chmod +x run-dashboard.sh`, then try the start command again.
- **`Port 8000 is in use`** — that's fine; the script frees it and keeps
  going. If not, close any old Terminal windows and try again.
- **The page says "DEMO MODE"** — Neo can't see your keys. Make sure you ran
  the command with `source neo.env` at the front, and that the `neo.env` file
  is in the `neo-main` folder.
- **Anything else** — copy the red text from Terminal and send it to Mariah.
