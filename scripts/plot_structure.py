"""Plot geometric definitions extracted from MPH; this is not a COMSOL render."""
import csv
import json
import re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT / 'docs/model_inventory.json').read_text(encoding='utf-8'))
cylinders = []
for feature in r['geometry']:
    if feature['op'] != 'Cylinder':
        continue
    settings = {v['name']: v for v in feature['settings']}
    xyz = re.findall(r"'([^']*)'", settings['p:pos']['valueMatrix'])
    cylinders.append((feature['tag'], float(xyz[0].replace('[nm]', '')),
                      float(xyz[1].replace('[nm]', '')), 200.0, 220.0))
with (ROOT / 'docs/cylinder_positions_nm.csv').open('w', newline='', encoding='utf-8') as stream:
    writer = csv.writer(stream)
    writer.writerow(['tag', 'x_nm', 'y_nm', 'radius_nm', 'height_nm'])
    writer.writerows(cylinders)
fig, ax = plt.subplots(figsize=(7.2, 7.8), facecolor='#f7f9fc')
ax.set_facecolor('#edf2fa')
ax.add_patch(Rectangle((-440, -440), 3820, 3820, fc='#d7e1f0', ec='#193b61', lw=2))
for tag, x, y, radius, height in cylinders:
    ax.add_patch(Circle((x, y), radius, fc='#f6fcff', ec='#146d91', lw=1.25))
    ax.text(x, y, tag.replace('qcyl', ''), ha='center', va='center', fontsize=7, color='#17516b')
ax.set_aspect('equal')
ax.set(xlim=(-650, 3590), ylim=(-650, 3590), xlabel='x (nm)', ylabel='y (nm)')
ax.set_title('NUMBER37: geometric top view\n37 cylinders | R = 200 nm | H = 220 nm', pad=15)
ax.grid(alpha=.16)
fig.text(.5, .025, 'Reconstructed from MPH geometry definitions; material domains and mesh are not rendered.\n'
         'Actual block width: 3820 nm. Circle numbers match qcyl1 ... qcyl37.',
         ha='center', va='bottom', fontsize=8, color='#435367')
fig.tight_layout(rect=(0, .07, 1, 1))
fig.savefig(ROOT / 'docs/structure_top_view.png', dpi=180)
plt.close(fig)
print('Saved geometric preview and 37 cylinder coordinates.')
