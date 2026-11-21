PITLOG: offline pit-lane logger for iPad 1 and Android
======================================================

What's in this folder
---------------------
index.html            The app (same file for iPad and Android)
icon.png              iPad home screen icon
pitlog.appcache       Tells the iPad which files to keep for offline use
sw.js                 Tells Android phones/tablets which files to keep offline
manifest.webmanifest  Makes PitLog installable on Android
icon-192.png, icon-512.png   Android icons
serve.py              Laptop helper: installs on the iPad, receives Wi-Fi syncs,
                      merges Android backup files into the laptop history
README.txt            This guide

How it works
------------
PitLog lives on the iPad and works with no internet and no Wi-Fi.
When the iPad and the laptop are on the same Wi-Fi, you tap "Sync to laptop
now". The laptop keeps a dated backup plus one running history of every
session and run, as spreadsheet files you can open in Excel or Google Sheets.
The Wi-Fi never needs internet. A phone hotspot with mobile data turned off
works fine.


INSTALL DAY CHECKLIST (about 15 minutes)
========================================
Bring: the iPad (charged), a laptop with this folder on it, and a Wi-Fi both
can join (home router or a phone hotspot).

[ ] 1. Python 3 on the laptop
       Mac: open Terminal, type  python3 --version
       Windows: open Command Prompt, type  py --version
       If it says 3.7 or higher, good. If not, install Python from
       python.org first (on Windows tick "Add Python to PATH").

[ ] 2. Give the laptop a fixed address (important, do it once)
       The iPad remembers PitLog by the laptop's address. If the address
       changes later, the iPad treats it as a new app with empty data when
       you update. Easiest ways:
       - Always use the same phone hotspot or router, and in the router or
         hotspot settings "reserve" the laptop's IP address, or
       - Just write down the address in step 4 and check it matches each
         time before you update.

[ ] 3. Start the laptop helper
       Mac: in Terminal, go to this folder (type cd, a space, drag the
            folder into the window, press Enter), then type:  python3 serve.py
       Windows: open the folder, click the address bar, type cmd, press
            Enter, then type:  py serve.py
            Click "Allow" if the Windows firewall asks.

[ ] 4. Write down the address it prints, like
       http://192.168.1.23:8000/index.html

[ ] 5. On the iPad: join the same Wi-Fi, open Safari, type that address.

[ ] 6. Wait about 10 seconds. Then tap the Share button (box with arrow)
       > Add to Home Screen > Add.

[ ] 7. Close Safari. Open PitLog from the new home screen icon, still on
       the Wi-Fi. Go to Data & Sync. The top line should say
       "Saved for offline use". If it says "Saving...", wait and reopen.

[ ] 8. Offline test: on the iPad turn Wi-Fi OFF (Settings > Wi-Fi). Close
       PitLog fully (double-press Home, swipe it up). Open it from the
       icon again. It must open normally.

[ ] 9. Sync test: Wi-Fi back ON. In PitLog: Sessions > + New session >
       + New run, type anything. Data & Sync > "Sync to laptop now".
       You should see "Sync OK" in green, and the laptop window shows
       "Synced at ...". Check the laptop folder now has "backups" and
       "history" folders.

[ ] 10. Fill in Data & Sync > Settings once: car name, defaults for new
        sessions (drivers, car number, transponder, class), units, target
        hot pressures, allowed +/- range, minimum tread.

[ ] 11. Delete the test session (answer OK to "was this a mistake") and
        sync again. Done. You can stop the laptop helper with Ctrl+C.

Always open PitLog from the home screen icon, not from a Safari tab.
They may keep separate data.

If step 7 or 8 fails, tell me what Data & Sync says at the top.


USING IT AT THE TRACK
=====================
Each session (practice, quali, race): Sessions > + New session. Drivers,
car number, transponder and class fill in from your defaults.

Each time the car goes out: + New run
  Before (cold):  tyre set, cold pressures, tread, fuel, setup changes.
                  Tap "Now" next to Time out when the car leaves.
  After (hot):    tap "Now" for Time in, then laps, lap times, hot
                  pressures, tyre temps, tread, fuel left, driver feedback,
                  pit stop work. Live pressure build and tyre temps show
                  under each box as you type.
  Results:        checks and warnings, recommended cold pressures for the
                  next run, tyre temp readings, lap stats, fuel per lap,
                  fuel for the next run, wear and laps to minimum tread.

"Start Run 2" copies tyre set, tread, fuel (fuel left + fuel added) and ride
heights from the previous run. A blue banner lists what was copied so you
check it before the car leaves. Recommended cold pressures are never filled
in by themselves. You tap a button, see the numbers, and confirm.

Everything saves by itself as you type. Last save time shows top right.

Tools: fuel calculator, pressure vs temperature, corner weights, unit
converter, and a stopwatch that keeps running if the app reloads.
Analysis: session summary, trend chart by run, compare two runs, tyre set
history (heat cycles and laps per set).


ENDURANCE: SEVERAL DRIVERS SHARING ONE CAR
==========================================
In the session, list up to 4 drivers. Each run (stint) has a "Driver this
stint" picker on the Before tab. When you tick "Driver change" in the Pit
stop box, the next run starts with the next driver on the list. The blue
banner says so, and you can pick someone else if the order changes.

Drive time rules are optional, per session: race length, min drive per
driver, max drive per driver, max stint (all in minutes). Leave any empty if
your series doesn't have it. The session screen then shows a "Drivers and
drive time" box with:
- each driver's stints, drive time, laps, best lap, clean average, fuel per lap
- how much each driver still needs for the minimum, and has left before the max
- race time left (the race clock starts at the first Time out)
- red and orange warnings: stint over the max, driver over max drive time,
  minutes left before a limit (Settings > "Warn before drive time limits",
  5 minutes unless you change it), and not enough race time left for every
  driver to reach the minimum
The After tab shows "Stint so far" with the limit. Numbers update every 15
seconds while the car is out.

Drive time counts from Time out to Time in as you log them, so tap "Now" at
the right moments. Check how your series measures drive time (pit exit,
timing line) and leave yourself a margin.


SEVERAL CARS
============
Make one session per car with its own car number. On a session screen,
"Add another car to this session" copies the event, track, date, type,
class and drive time rules into a new session. You then fill in that car's
number, transponder and drivers. When there's more than one car number, the
Sessions screen shows buttons to filter by car. Tyre sets are tracked per
car, so S1 on car 27 and S1 on car 28 stay separate.


ANDROID VERSION
===============
Same app, same features, plus things only newer phones can do (see below).
It works offline once installed. Installing needs internet ONE time, because
Android only lets a web app work offline when it comes from a secure (https)
address. The free way is GitHub Pages:

1. On github.com, make a new repository called pitlog (Public).
2. "Add file" > "Upload files" > upload everything in this folder > Commit.
3. Repository Settings > Pages > Source: "Deploy from a branch",
   Branch: main, folder: / (root) > Save. Wait 1 to 2 minutes.
4. On the Android phone, open Chrome and go to
   https://YOUR-GITHUB-NAME.github.io/pitlog/
5. Chrome menu (three dots) > "Install app" or "Add to Home screen".
   (Data & Sync also shows an "Install PitLog" button when Chrome offers it.)
6. Open PitLog from the home screen. Data & Sync should say
   "Saved for offline use". Test: turn on airplane mode, close and reopen.

Your data is never uploaded to GitHub. GitHub only hands out the empty app;
everything you log stays on the phone. Anyone with the link can open an empty
copy of the app, nothing more.

Backups on Android (the laptop Wi-Fi sync is blocked by Chrome for apps
installed from https, so use files instead):
- Data & Sync > "Save backup file" puts a .json file in Downloads.
- "Share backup" sends it to Google Drive, Gmail, Quick Share, and so on.
- "Open a backup file to restore" loads a backup back in.
- Into the laptop history: copy the file to the laptop, then run
    python3 serve.py --merge pitlog-backup-....json
  It updates history/runs.csv and keeps a copy in backups/.
- Onto the iPad: put the file in the laptop's backups folder, start
  serve.py, and on the iPad use "Get latest backup from laptop" > Restore.
The iPad and Android copies do NOT share data by themselves. Move data
between them with backup files as above.

Updating the Android version: upload the new files to the same GitHub
repository. Change the VERSION line at the top of sw.js (for example
pitlog-1.3.1), or phones keep the old copy. Phones get the update the next
time they open PitLog with internet, and it asks to reload.

Extras that only work on newer phones and tablets (Data & Sync > Settings):
- Keep the screen on while PitLog is open.
- Vibrate when a drive time warning appears.


NEW IN 1.3 (iPad and Android)
=============================
Race strategy (Tools > Strategy): enter race length (laps or minutes),
average lap time, fuel per lap, tank, refuel speed, pit lane loss, tyre
change time, tyre life and any rules (min stops, max stint, min stop time).
It tries several stop counts and shows which ones work, the laps per stint,
fuel to add at each stop, tyre changes, time in the pits and the race time
(or laps done in a timed race). "Fill from current session" copies lap time,
fuel per lap and rules from your logged runs. Tap a row for the stop-by-stop
plan. Lap time is treated as constant (no traffic, safety cars or fuel
weight), so use it to compare options and adjust on the day.

Pre-run checklist: Data & Sync > Settings > one item per line. Every run's
Before tab shows the ticks, and Results warns about anything not ticked
once the car has gone out.

Stopwatch to lap times: in Tools > Stopwatch, press Split each time the car
crosses the line, then "Add splits as lap times to Run N".


SYNCING TO THE LAPTOP
=====================
1. Laptop: start serve.py (Install day step 3).
2. iPad: join the same Wi-Fi.
3. PitLog > Data & Sync > Sync to laptop now.

The orange "to sync" badge at the top shows how many changes are waiting.
A yellow banner on the Sessions screen warns you after 24 hours without a
sync. Sync after every session if you can, at least after every event day.

What you get on the laptop
  backups/   One full copy of the iPad per sync, named by date and time.
             Never overwritten. Restore one onto the iPad with
             Data & Sync > "Get latest backup from laptop" then "Restore".
  history/   runs.csv       one row per run, every run ever synced
             sessions.csv   one row per session
             sync-log.csv   what came in and when
             pitlog-history.json   the same history in the app's format

Rules the laptop follows
- Runs are matched by a hidden ID, so syncing twice never makes duplicates.
- A newer version of a run replaces the older one. An older one never
  replaces a newer one.
- Nothing is ever removed from the history.
- Deleting a run on the iPad marks it in the "Deleted" column on the next
  sync. When you delete a session the app asks if it was a mistake: OK marks
  it deleted in the history, Cancel keeps it (use that when you just want
  to free space on the iPad).
- Units in the laptop files are always psi, deg C, litres and mm, whatever
  the iPad shows, so the history stays consistent.

Analysis on the laptop: open history/runs.csv in Excel, or in Google Sheets
use File > Import > Upload. Close runs.csv in Excel before syncing, or the
sync shows an error asking you to close it (your backup is still saved).

If sync says it could not reach the laptop: check the iPad and laptop are on
the same Wi-Fi, serve.py is running, and the address matches. You can type
the laptop address into the box on the Data & Sync screen if it changed.


END OF SEASON: FREEING SPACE ON THE IPAD
========================================
Safari gives PitLog about 5 MB. Data & Sync shows how much is used. When it
gets past a few thousand KB:
1. Sync to the laptop and check it says "Sync OK".
2. Data & Sync > "Remove all sessions and runs from this iPad".
The laptop history keeps everything. You can undo once.


UPDATING PITLOG LATER
=====================
1. Sync to the laptop first.
2. Put the new files in the folder. Change the "# PitLog ..." line in
   pitlog.appcache (bump the version), or the iPad won't notice the update.
3. Start serve.py. The laptop must have the SAME address as on install day.
4. Open PitLog on the iPad while on that Wi-Fi. It asks to reload with the
   new version. Your data stays.


KNOWN LIMITS
============
- Offline on the iPad 1 comes from the laptop install. Offline on Android
  (and newer iPhones/iPads, Chrome, Edge) comes from the https install
  described in ANDROID VERSION. A newer device opened from the laptop
  address works, but only while connected to the laptop.
- Lap times use a dot for decimals: 1:32.456 or 92.456.
- Tyre "Reading" hints only appear once you set the thresholds in
  Settings. Use your tyre supplier's numbers. They are hints, not rules.
- Tested in desktop browsers at iPad screen size, with a real laptop helper,
  and checked for code the iPad 1 can run. Not yet tested on a real iPad 1,
  which is what the install day checklist is for.
