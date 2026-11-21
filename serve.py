#!/usr/bin/env python3
"""
PitLog laptop helper: installs the app on the iPad and receives Wi-Fi syncs.

Run this on a laptop that is on the same Wi-Fi as the iPad. The Wi-Fi does
NOT need internet (a phone hotspot with mobile data off works).

What it does:
  1. Install / update: shares the PitLog files so the iPad can save them
     for offline use.
  2. Sync: when you tap "Sync to laptop now" in PitLog, the iPad sends all
     its data here. Two things happen:
       - backups/pitlog-backup-<date>-<time>.json
             a full copy of the iPad at that moment (never overwritten,
             can be restored onto the iPad from the app)
       - history/
             pitlog-history.json  every session and run ever synced, merged
             runs.csv             one row per run, open in Excel or import
                                  into Google Sheets for analysis
             sessions.csv         one row per session
             sync-log.csv         what came in and when
     Newer data replaces older data (matched by a hidden ID per run, so no
     duplicates). Nothing is ever removed from the history. Runs deleted on
     the iPad as mistakes are marked in a "Deleted" column.

Units in the history files are ALWAYS psi, deg C, litres and mm,
whatever the iPad displays.

How to run (Python 3.7 or newer, nothing else to install):
    Mac / Linux:  python3 serve.py
    Windows:      py serve.py
Press Ctrl+C to stop.

Adding a backup file from the Android app (or any PitLog backup file) to the
laptop history, without starting the server:
    python3 serve.py --merge pitlog-backup-20261121-1430.json
"""
import csv
import datetime
import http.server
import json
import os
import socket
import sys
import threading

PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(HERE, 'backups')
HISTORY_DIR = os.path.join(HERE, 'history')
HISTORY_FILE = os.path.join(HISTORY_DIR, 'pitlog-history.json')
MAX_BYTES = 50 * 1024 * 1024
CORNERS = ['FL', 'FR', 'RL', 'RR']
LOCK = threading.Lock()

# Only these files are shared. Nothing else on the laptop can be read.
FILES = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/index.html': ('index.html', 'text/html; charset=utf-8'),
    '/icon.png': ('icon.png', 'image/png'),
    '/pitlog.appcache': ('pitlog.appcache', 'text/cache-manifest'),
    '/sw.js': ('sw.js', 'application/javascript; charset=utf-8'),
    '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
    '/icon-192.png': ('icon-192.png', 'image/png'),
    '/icon-512.png': ('icon-512.png', 'image/png'),
}


# ---------------------------------------------------------------- helpers

def now_text():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def ms_text(ms):
    if not ms:
        return ''
    try:
        return datetime.datetime.fromtimestamp(ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ''


def g(obj, path):
    """Safe nested get: g(run, 'a.p.FL')."""
    for key in path.split('.'):
        if not isinstance(obj, dict):
            return ''
        obj = obj.get(key)
    return '' if obj is None else obj


def write_atomic(path, text):
    tmp = path + '.part'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    os.replace(tmp, path)


def backup_files():
    if not os.path.isdir(BACKUP_DIR):
        return []
    names = [n for n in os.listdir(BACKUP_DIR) if n.startswith('pitlog-backup-') and n.endswith('.json')]
    # Oldest first, newest last (by save time, then name).
    return sorted(names, key=lambda n: (os.path.getmtime(os.path.join(BACKUP_DIR, n)), n))


# ---------------------------------------------------------------- history

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {'sessions': {}, 'runs': {}, 'calc': {}, 'deleted': {}, 'created': now_text()}
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        h = json.load(f)
    for k in ('sessions', 'runs', 'calc', 'deleted'):
        h.setdefault(k, {})
    return h


def merge(history, db, calcs):
    """Add new items, replace older versions with newer ones, mark deletions. Never removes."""
    counts = {'inserted': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
    tomb_ids = set(t.get('id') for t in db.get('tomb', []) if isinstance(t, dict))
    log_rows = []

    def upsert(kind, rec):
        rid = rec.get('id')
        if not rid:
            return
        table = history[kind]
        old = table.get(rid)
        new_ver = rec.get('modified') or 0
        if old is None:
            table[rid] = rec
            result = 'inserted'
        elif new_ver > (old.get('modified') or 0):
            table[rid] = rec
            result = 'updated'
        else:
            result = 'unchanged'
        counts[result] += 1
        if result != 'unchanged' and kind == 'runs':
            history['calc'][rid] = calcs.get(rid, {})
        # Present on the iPad and not deleted there: clear any old deleted mark (e.g. after an undo).
        if rid in history['deleted'] and rid not in tomb_ids:
            del history['deleted'][rid]
            log_rows.append([now_text(), 'undelete', kind[:-1], rid, '', 'restored on iPad'])
        if result != 'unchanged':
            label = (rec.get('event') or '') if kind == 'sessions' else 'run %s' % rec.get('no', '')
            log_rows.append([now_text(), 'sync', kind[:-1], rid, label, result])

    for s in db.get('sessions', []):
        if isinstance(s, dict):
            upsert('sessions', s)
    for r in db.get('runs', []):
        if isinstance(r, dict):
            upsert('runs', r)
    for t in db.get('tomb', []):
        if not isinstance(t, dict):
            continue
        tid = t.get('id')
        if (tid in history['runs'] or tid in history['sessions']) and tid not in history['deleted']:
            history['deleted'][tid] = ms_text(t.get('t')) or now_text()
            counts['deleted'] += 1
            log_rows.append([now_text(), 'delete', t.get('kind', ''), tid, '', 'marked deleted'])
    history['updated'] = now_text()
    return counts, log_rows


def lineup(s):
    names = []
    for n in (s.get('drivers') or [s.get('driver', '')]):
        n = str(n or '').strip()
        if n and n not in names:
            names.append(n)
    return names


def run_driver(r, s):
    d = str(r.get('driver') or '').strip()
    if d:
        return d
    lu = lineup(s)
    return lu[0] if lu else ''


def session_columns():
    return [
        ('Session ID', lambda s: s.get('id', '')),
        ('Session date', lambda s: g(s, 'date')),
        ('Event', lambda s: g(s, 'event')),
        ('Track', lambda s: g(s, 'track')),
        ('Session type', lambda s: g(s, 'type')),
        ('Drivers', lambda s: ' / '.join(lineup(s))),
        ('Car', lambda s: g(s, 'car')),
        ('Car number', lambda s: g(s, 'carNo')),
        ('Transponder', lambda s: g(s, 'transponder')),
        ('Class', lambda s: g(s, 'cls')),
        ('Race length (min)', lambda s: g(s, 'raceLen')),
        ('Min drive per driver (min)', lambda s: g(s, 'minDrive')),
        ('Max drive per driver (min)', lambda s: g(s, 'maxDrive')),
        ('Max stint (min)', lambda s: g(s, 'maxStint')),
        ('Notes', lambda s: g(s, 'notes')),
        ('Created on iPad', lambda s: ms_text(s.get('created'))),
        ('Last changed on iPad', lambda s: ms_text(s.get('modified'))),
    ]


def run_columns():
    cols = [
        ('Run ID', lambda r, c, s: r.get('id', '')),
        ('Session ID', lambda r, c, s: r.get('sessionId', '')),
        ('Session date', lambda r, c, s: g(s, 'date')),
        ('Event', lambda r, c, s: g(s, 'event')),
        ('Track', lambda r, c, s: g(s, 'track')),
        ('Session type', lambda r, c, s: g(s, 'type')),
        ('Car number', lambda r, c, s: g(s, 'carNo')),
        ('Class', lambda r, c, s: g(s, 'cls')),
        ('Run', lambda r, c, s: g(r, 'no')),
        ('Driver', lambda r, c, s: run_driver(r, s)),
        ('Tyre set', lambda r, c, s: g(r, 'tyreSet')),
        ('Compound', lambda r, c, s: g(r, 'compound')),
        ('Weather', lambda r, c, s: g(r, 'weather')),
        ('Ambient (C)', lambda r, c, s: g(r, 'ambient')),
        ('Track temp (C)', lambda r, c, s: g(r, 'trackT')),
        ('Time out', lambda r, c, s: ms_text(r.get('timeOut'))),
        ('Time in', lambda r, c, s: ms_text(r.get('timeIn'))),
        ('Stint time (s)', lambda r, c, s: g(c, 'trackSec')),
        ('Laps', lambda r, c, s: g(c, 'laps')),
        ('Best lap (s)', lambda r, c, s: g(c, 'best')),
        ('Clean avg (s)', lambda r, c, s: g(c, 'cleanAvg')),
        ('Clean laps', lambda r, c, s: g(c, 'cleanN')),
        ('Std dev (s)', lambda r, c, s: g(c, 'sd')),
        ('Lap times', lambda r, c, s: g(r, 'a.lapTimes')),
    ]

    def add(name, fn):
        cols.append((name, fn))

    for k in CORNERS:
        add('Cold %s (psi)' % k, lambda r, c, s, k=k: g(r, 'b.p.' + k))
    for k in CORNERS:
        add('Hot %s (psi)' % k, lambda r, c, s, k=k: g(r, 'a.p.' + k))
    for k in CORNERS:
        add('Build %s (psi)' % k, lambda r, c, s, k=k: g(c, 'build.' + k))
    for k in CORNERS:
        add('Rec cold %s (psi)' % k, lambda r, c, s, k=k: g(c, 'rec.' + k))
    for k in CORNERS:
        add('Temp %s inner (C)' % k, lambda r, c, s, k=k: g(r, 'a.t.%s.i' % k))
        add('Temp %s middle (C)' % k, lambda r, c, s, k=k: g(r, 'a.t.%s.m' % k))
        add('Temp %s outer (C)' % k, lambda r, c, s, k=k: g(r, 'a.t.%s.o' % k))
        add('Temp %s avg (C)' % k, lambda r, c, s, k=k: g(c, 'tAvg.' + k))
        add('Spread %s in-out (C)' % k, lambda r, c, s, k=k: g(c, 'spread.' + k))
        add('Mid vs edges %s (C)' % k, lambda r, c, s, k=k: g(c, 'mid.' + k))
    for k in CORNERS:
        add('Brake %s (C)' % k, lambda r, c, s, k=k: g(r, 'a.brake.' + k))
    for k in CORNERS:
        add('Tread before %s (mm)' % k, lambda r, c, s, k=k: g(r, 'b.tread.' + k))
        add('Tread after %s (mm)' % k, lambda r, c, s, k=k: g(r, 'a.tread.' + k))
        add('Wear %s (mm)' % k, lambda r, c, s, k=k: g(c, 'wear.' + k))
    for name, fn in [
        ('Fuel before (L)', lambda r, c, s: g(r, 'b.fuel')),
        ('Fuel after (L)', lambda r, c, s: g(r, 'a.fuel')),
        ('Fuel used (L)', lambda r, c, s: g(c, 'fuelUsed')),
        ('Fuel per lap (L)', lambda r, c, s: g(c, 'fpl')),
        ('Fuel added (L)', lambda r, c, s: g(r, 'stop.fuelAdded')),
        ('Next run fuel (L)', lambda r, c, s: g(c, 'nextFuel')),
        ('Stop time (s)', lambda r, c, s: g(r, 'stop.dur')),
        ('New tyres', lambda r, c, s: 'yes' if g(r, 'stop.tyresChanged') is True else ''),
        ('Driver change', lambda r, c, s: 'yes' if g(r, 'stop.driverChange') is True else ''),
        ('Ride height F (mm)', lambda r, c, s: g(r, 'b.rhF')),
        ('Ride height R (mm)', lambda r, c, s: g(r, 'b.rhR')),
        ('Oil (C)', lambda r, c, s: g(r, 'a.oil')),
        ('Water (C)', lambda r, c, s: g(r, 'a.water')),
        ('Entry', lambda r, c, s: g(r, 'a.fbE')),
        ('Mid', lambda r, c, s: g(r, 'a.fbM')),
        ('Exit', lambda r, c, s: g(r, 'a.fbX')),
        ('Setup changes', lambda r, c, s: g(r, 'setup')),
        ('Notes', lambda r, c, s: g(r, 'a.notes')),
        ('Work done', lambda r, c, s: g(r, 'stop.work')),
        ('Warnings', lambda r, c, s: ' | '.join(c.get('warn') or []) if isinstance(c, dict) else ''),
        ('Created on iPad', lambda r, c, s: ms_text(r.get('created'))),
        ('Last changed on iPad', lambda r, c, s: ms_text(r.get('modified'))),
    ]:
        add(name, fn)
    return cols


def write_csvs(history):
    sessions = history['sessions']
    deleted = history['deleted']

    def sess_key(s):
        return (g(s, 'date') or '', s.get('created') or 0)

    scols = session_columns()
    rows = [[n for n, _ in scols] + ['Deleted']]
    for s in sorted(sessions.values(), key=sess_key):
        rows.append([fn(s) for _, fn in scols] + [deleted.get(s.get('id'), '')])
    write_csv(os.path.join(HISTORY_DIR, 'sessions.csv'), rows)

    rcols = run_columns()
    rows = [[n for n, _ in rcols] + ['Deleted']]

    def run_key(r):
        s = sessions.get(r.get('sessionId'), {})
        return (g(s, 'date') or '', s.get('created') or 0, r.get('no') or 0)

    for r in sorted(history['runs'].values(), key=run_key):
        s = sessions.get(r.get('sessionId'), {})
        c = history['calc'].get(r.get('id'), {}) or {}
        rows.append([fn(r, c, s) for _, fn in rcols] + [deleted.get(r.get('id'), '')])
    write_csv(os.path.join(HISTORY_DIR, 'runs.csv'), rows)


def write_csv(path, rows):
    tmp = path + '.part'
    # utf-8-sig so Excel shows special characters correctly
    with open(tmp, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(rows)
    try:
        os.replace(tmp, path)
    except PermissionError:
        os.remove(tmp)
        raise RuntimeError('%s is open in another program (probably Excel). Close it on the laptop and sync again.' % os.path.basename(path))


def append_sync_log(rows):
    path = os.path.join(HISTORY_DIR, 'sync-log.csv')
    new = not os.path.exists(path)
    with open(path, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['When', 'Action', 'Type', 'ID', 'Label', 'Result'])
        w.writerows(rows)


# ---------------------------------------------------------------- web server

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = 'PitLog'

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def send_json(self, code, obj):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def path_only(self):
        return self.path.split('?')[0].split('#')[0]

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        path = self.path_only()
        if path == '/backups/latest':
            return self.get_latest_backup()
        if path not in FILES:
            return self.send_json(404, {'ok': False, 'err': 'Not found'})
        name, ctype = FILES[path]
        full = os.path.join(HERE, name)
        if not os.path.exists(full):
            return self.send_json(404, {'ok': False, 'err': 'Missing file ' + name})
        with open(full, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        if name == 'pitlog.appcache':
            # The iPad must always re-check this file, otherwise updates never arrive.
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_cors()
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path_only() != '/sync':
            return self.send_json(404, {'ok': False, 'err': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return self.send_json(400, {'ok': False, 'err': 'The data arrived empty. Try again.'})
        if length > MAX_BYTES:
            return self.send_json(413, {'ok': False, 'err': 'Data is bigger than 50 MB.'})
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode('utf-8'))
            db = payload['db']
            calcs = payload.get('calc') or {}
        except Exception:
            return self.send_json(400, {'ok': False, 'err': 'The data arrived damaged (not readable). Try again.'})
        if not isinstance(db, dict) or not isinstance(db.get('sessions'), list) or not isinstance(db.get('runs'), list):
            return self.send_json(400, {'ok': False, 'err': 'That is not PitLog data.'})

        with LOCK:
            try:
                # 1. Full dated backup first, so nothing is lost even if the merge fails.
                os.makedirs(BACKUP_DIR, exist_ok=True)
                os.makedirs(HISTORY_DIR, exist_ok=True)
                t = datetime.datetime.now()
                stamp = t.strftime('%Y%m%d-%H%M%S-') + '%03d' % (t.microsecond // 1000)
                name = 'pitlog-backup-%s.json' % stamp
                n = 2
                while os.path.exists(os.path.join(BACKUP_DIR, name)):
                    name = 'pitlog-backup-%s-%d.json' % (stamp, n)
                    n += 1
                write_atomic(os.path.join(BACKUP_DIR, name), json.dumps(db))

                # 2. Merge into the running history.
                history = load_history()
                counts, log_rows = merge(history, db, calcs)
                write_atomic(HISTORY_FILE, json.dumps(history))
                write_csvs(history)
                log_rows.append([now_text(), 'backup', '', '', name, '%d sessions, %d runs on iPad' % (len(db['sessions']), len(db['runs']))])
                append_sync_log(log_rows)
            except Exception as e:
                print('  SYNC PROBLEM: %s' % e)
                return self.send_json(500, {'ok': False, 'err': str(e)})

        counts['sessions'] = len(history['sessions'])
        counts['runs'] = len(history['runs'])
        print('  Synced at %s: %d new, %d updated, %d marked deleted. History: %d sessions, %d runs. Backup: backups/%s'
              % (now_text(), counts['inserted'], counts['updated'], counts['deleted'], counts['sessions'], counts['runs'], name))
        self.send_json(200, {'ok': True, 'file': name, 'sessions': len(db['sessions']), 'runs': len(db['runs']), 'history': counts})

    def get_latest_backup(self):
        names = backup_files()
        if not names:
            return self.send_json(404, {'ok': False, 'err': 'No backups on this laptop yet.'})
        name = names[-1]
        try:
            with open(os.path.join(BACKUP_DIR, name), 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return self.send_json(500, {'ok': False, 'err': 'Latest backup file %s could not be read.' % name})
        print('  Sent latest backup to iPad: backups/%s' % name)
        self.send_json(200, {'ok': True, 'file': name, 'data': data})

    def log_message(self, fmt, *args):
        if args and isinstance(args[0], str) and args[0].startswith('GET') and '/backups/' not in args[0]:
            sys.stdout.write('  iPad asked for: %s\n' % args[0])


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def merge_file(path):
    """Merge a PitLog backup file (from the Android app's Save/Share backup) into the history."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print('Could not read %s: %s' % (path, e))
        return 1
    if isinstance(data, dict) and isinstance(data.get('db'), dict):
        db, calcs = data['db'], data.get('calc') or {}
    else:
        db, calcs = data, {}
    if not isinstance(db, dict) or not isinstance(db.get('sessions'), list) or not isinstance(db.get('runs'), list):
        print('%s is not PitLog data.' % path)
        return 1
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    t = datetime.datetime.now()
    name = 'pitlog-backup-%s-%03d-merged.json' % (t.strftime('%Y%m%d-%H%M%S'), t.microsecond // 1000)
    write_atomic(os.path.join(BACKUP_DIR, name), json.dumps(db))
    history = load_history()
    counts, log_rows = merge(history, db, calcs)
    write_atomic(HISTORY_FILE, json.dumps(history))
    try:
        write_csvs(history)
    except RuntimeError as e:
        print(str(e))
        return 1
    log_rows.append([now_text(), 'merge file', '', '', os.path.basename(path), '%d sessions, %d runs in file' % (len(db['sessions']), len(db['runs']))])
    append_sync_log(log_rows)
    print('Merged %s: %d new, %d updated, %d marked deleted. History now: %d sessions, %d runs.'
          % (os.path.basename(path), counts['inserted'], counts['updated'], counts['deleted'], len(history['sessions']), len(history['runs'])))
    if not calcs:
        print('Note: this file has no calculated columns (best lap, fuel per lap...). Files saved from PitLog 1.3 or newer include them.')
    print('A copy was also saved as backups/%s' % name)
    return 0


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--merge':
        sys.exit(merge_file(sys.argv[2]))
    if sys.version_info < (3, 7):
        print('Please use Python 3.7 or newer.')
        sys.exit(1)
    for path, (name, _) in FILES.items():
        if not os.path.exists(os.path.join(HERE, name)):
            print('Missing file: %s. Keep all PitLog files in the same folder as serve.py.' % name)
            sys.exit(1)
    ip = lan_ip()
    try:
        server = http.server.ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    except OSError:
        print('Port %d is busy. Is serve.py already running in another window?' % PORT)
        sys.exit(1)
    print('')
    print('PitLog laptop helper is running.')
    print('On the iPad, open Safari and go to:')
    print('')
    print('    http://%s:%d/index.html' % (ip, PORT))
    print('')
    print('Write this address down. Use the SAME address every time you update PitLog,')
    print('or the iPad will treat it as a new app with empty data.')
    print('Backups go to:  %s' % BACKUP_DIR)
    print('History goes to: %s  (open runs.csv in Excel or Google Sheets)' % HISTORY_DIR)
    print('Backups so far: %d' % len(backup_files()))
    print('Press Ctrl+C to stop.')
    print('')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
